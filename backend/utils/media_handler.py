import os
import tempfile
import mimetypes
import threading
import cv2
from datetime import datetime
from django.conf import settings


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

VIDEO_MAX_DURATION  = 30            # seconds — input limit
VIDEO_MAX_WIDTH     = 1920          # FHD max input resolution
VIDEO_MAX_HEIGHT    = 1080          # FHD max input resolution
VIDEO_TARGET_WIDTH  = 1280          # HD 720p output width
VIDEO_TARGET_HEIGHT = 720           # HD 720p output height
VIDEO_TARGET_FPS    = 30

IMAGE_SAVE_FORMAT        = '.jpg'   # all images stored as JPEG
IMAGE_TARGET_MIN_MB      = 2.0     # compressed floor — small images stay above this
IMAGE_TARGET_MAX_MB      = 5.0     # compressed ceiling
IMAGE_LARGE_PREFER_MB    = 5.0     # for inputs >10 MB, binary-search aims at this target
IMAGE_LARGE_THRESHOLD_MB = 10.0    # input size above which we prefer the upper bound
IMAGE_QUALITY_MAX        = 95      # JPEG quality upper bound
IMAGE_QUALITY_MIN        = 10      # JPEG quality lower bound — stop trying below this


class FileManager:
    """Manages file uploads and operations for users."""

    def __init__(self, user_id):
        self.user_id   = user_id
        self.base_path = os.path.join(settings.MEDIA_ROOT, 'Uploaded_Files', str(user_id))
        self.base_url  = f"{settings.MEDIA_URL}Uploaded_Files/{user_id}"
        
        # Define the custom temp directory
        self.custom_temp_dir =os.path.join(settings.MEDIA_ROOT,'temp_uploads')
        if not os.path.exists(self.custom_temp_dir):
            os.makedirs(self.custom_temp_dir, exist_ok=True)


    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def save_profile_file(self, file, file_purpose, allowed_extensions=None, max_size_mb=None):
        IMAGE_PURPOSES = ['profile-pic', 'verification-doc-front', 'verification-doc-back']
    
        # Images have no raw size limit — compressed to 2–5 MB on save
        if max_size_mb is None and file_purpose in IMAGE_PURPOSES:
            max_size_mb = 35000   # explicit — no limit
        elif max_size_mb is None:
            max_size_mb = 10     # non-image profile files (e.g. PDFs)

        return self._save_file(
            file=file,
            category='profile',
            file_purpose=file_purpose,
            allowed_extensions=allowed_extensions,
            max_size_mb=max_size_mb,
        )


    def save_product_file(self, file, product_id, file_type, sequence=None,
                          allowed_extensions=None, max_size_mb=None):
        """
        Save product-related files (images / videos).

        Images  → accepted at ANY size/format, converted and stored as JPEG
                  in the 2–4 MB range via adaptive quality search.

        Videos  → validated ≤30s and ≤FHD resolution before saving.
                  Saved as raw immediately so the API responds fast.
                  Converted to 720p MP4 in a background daemon thread;
                  raw file is replaced when done.

        Response includes 'converting': True/False.

        Args:
            file              : Uploaded file object
            product_id        : Product ID
            file_type         : 'img' or 'vid'
            sequence          : Sequence number (auto-generated if None)
            allowed_extensions: Overrides defaults if provided
            max_size_mb       : Raw upload ceiling (no limit for img; 200 MB for vid)

        Returns:
            dict: Result with success status and file info
        """
        if file_type == 'vid':
            check = self._validate_video_properties(file)
            if not check['success']:
                return check
            if max_size_mb is None:
                max_size_mb = 200   # accept any FHD file before conversion

        elif file_type == 'img':
            # No raw upload size limit — we will compress on the way out
            max_size_mb = 9999

        return self._save_file(
            file=file,
            category='product',
            file_purpose=file_type,
            product_id=product_id,
            sequence=sequence,
            allowed_extensions=allowed_extensions,
            max_size_mb=max_size_mb,
        )


    def delete_file(self, category, file_name):
        """
        Delete a specific file.

        Returns:
            dict: {'success': bool, 'message'/'error': str}
        """
        if not self._is_valid_category(category):
            return {'success': False, 'error': 'Invalid category'}

        file_path = os.path.join(self.base_path, category, file_name)
        if not self._is_safe_path(file_path):
            return {'success': False, 'error': 'Invalid file path'}

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return {'success': True, 'message': 'File deleted successfully'}
            return {'success': False, 'error': 'File not found'}
        except PermissionError as e:
            return {'success': False, 'error': f'Permission denied: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


    def delete_product_files(self, product_id):
        """
        Delete all files for a specific product.

        Returns:
            dict: {'success': bool, 'partial': bool, 'deleted_count': int, 'errors': list|None}
        """
        product_dir = os.path.join(self.base_path, 'product')

        if not os.path.exists(product_dir):
            return {'success': True, 'deleted_count': 0, 'message': 'No product directory found'}

        deleted_count = 0
        errors = []

        try:
            for file_name in os.listdir(product_dir):
                if file_name.startswith(f"{product_id}-"):
                    result = self.delete_file('product', file_name)
                    if result['success']:
                        deleted_count += 1
                    else:
                        errors.append(f"{file_name}: {result['error']}")

            return {
                'success'      : len(errors) == 0,
                'partial'      : deleted_count > 0 and len(errors) > 0,
                'deleted_count': deleted_count,
                'errors'       : errors if errors else None,
            }
        except Exception as e:
            return {
                'success'      : False,
                'partial'      : deleted_count > 0,
                'deleted_count': deleted_count,
                'errors'       : [str(e)],
            }


    def get_file_info(self, category, file_name):
        """Get metadata about a specific file."""
        if not self._is_valid_category(category):
            return {'success': False, 'error': 'Invalid category'}

        file_path = os.path.join(self.base_path, category, file_name)
        if not self._is_safe_path(file_path):
            return {'success': False, 'error': 'Invalid file path'}

        if not os.path.exists(file_path):
            return {'success': False, 'error': 'File not found'}

        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            return {
                'success'  : True,
                'file_name': file_name,
                'file_path': file_path,
                'file_url' : f"{self.base_url}/{category}/{file_name}",
                'size'     : os.path.getsize(file_path),
                'mime_type': mime_type,
                'category' : category,
            }
        except Exception as e:
            return {'success': False, 'error': f'Error getting file info: {str(e)}'}


    def list_files(self, category=None):
        """List all files for this user."""
        if category and not self._is_valid_category(category):
            return {'success': False, 'error': 'Invalid category'}

        try:
            files_list = []
            categories = [category] if category else ['profile', 'product']

            for cat in categories:
                cat_dir = os.path.join(self.base_path, cat)
                if not os.path.exists(cat_dir):
                    continue

                for file_name in os.listdir(cat_dir):
                    file_path = os.path.join(cat_dir, file_name)
                    if os.path.isfile(file_path):
                        mime_type, _ = mimetypes.guess_type(file_path)
                        files_list.append({
                            'file_name': file_name,
                            'category' : cat,
                            'file_url' : f"{self.base_url}/{cat}/{file_name}",
                            'size'     : os.path.getsize(file_path),
                            'mime_type': mime_type,
                        })

            return {'success': True, 'files': files_list, 'count': len(files_list)}
        except Exception as e:
            return {'success': False, 'error': f'Error listing files: {str(e)}'}


    def verify_setup(self):
        """Verify MEDIA_ROOT is accessible and user base directory can be created."""
        try:
            if not os.path.exists(settings.MEDIA_ROOT):
                return {
                    'success': False,
                    'error'  : f'MEDIA_ROOT does not exist: {settings.MEDIA_ROOT}',
                    'tip'    : 'Create MEDIA_ROOT or check settings.py',
                }
            if not os.access(settings.MEDIA_ROOT, os.W_OK):
                return {
                    'success': False,
                    'error'  : f'MEDIA_ROOT is not writable: {settings.MEDIA_ROOT}',
                    'tip'    : 'Check directory permissions',
                }

            os.makedirs(self.base_path, exist_ok=True)

            if not os.path.exists(self.base_path):
                return {'success': False, 'error': f'Failed to create user directory: {self.base_path}'}

            return {
                'success'   : True,
                'base_path' : self.base_path,
                'writable'  : os.access(self.base_path, os.W_OK),
                'media_root': settings.MEDIA_ROOT,
                'message'   : 'Directory structure verified successfully',
            }
        except PermissionError as e:
            return {'success': False, 'error': f'Permission error: {str(e)}', 'tip': 'Check folder permissions'}
        except Exception as e:
            return {'success': False, 'error': f'Setup verification failed: {str(e)}'}


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — save pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _save_file(self, file, category, file_purpose, product_id=None,
                   sequence=None, allowed_extensions=None, max_size_mb=25*1024):

        if not self._is_valid_category(category):
            return {'success': False, 'error': 'Category must be "profile" or "product"'}

        if category == 'product' and not product_id:
            return {'success': False, 'error': 'product_id is required for product files'}

        if allowed_extensions is None:
            allowed_extensions = self._get_default_extensions(file_purpose)

        validation_result = self._validate_file(file, allowed_extensions, max_size_mb)
        if not validation_result['success']:
            return validation_result

        category_dir = os.path.join(self.base_path, category)

        try:
            os.makedirs(category_dir, exist_ok=True)
            if not os.path.exists(category_dir):
                return {'success': False, 'error': f'Failed to create directory: {category_dir}'}
            if not os.access(category_dir, os.W_OK):
                return {'success': False, 'error': f'Directory not writable: {category_dir}'}
        except PermissionError as e:
            return {'success': False, 'error': f'Permission denied creating directory: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Directory creation failed: {str(e)}'}

        timestamp = datetime.now().strftime('%m%d%Y-%H%M%S')

        # Route to specialised processors
        if file_purpose == 'img':
            return self._save_image(file, category_dir, product_id, sequence, timestamp)

        if file_purpose == 'vid':
            return self._save_video(file, category_dir, product_id, sequence, timestamp)

        # ── Profile / verification files ─────────────────────────────────────
        # Profile pictures and verification docs are also converted to JPEG
        # so the storage format is consistent across all image types.
        file_ext = os.path.splitext(file.name)[1].lower()
        is_image = file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif']

        if is_image:
            return self._save_profile_image(file, category_dir, file_purpose, timestamp)

        # Non-image profile file (e.g. PDF verification doc) — save as-is
        if category == 'profile':
            file_name = f"{file_purpose}-{timestamp}{file_ext}"
            counter   = 1
            temp_name = file_name
            while os.path.exists(os.path.join(category_dir, temp_name)):
                temp_name = f"{file_purpose}-{timestamp}-{counter}{file_ext}"
                counter += 1
            file_name = temp_name
        else:
            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id, file_purpose)
            file_name = f"{product_id}-{file_purpose}-{timestamp}-{sequence:03d}{file_ext}"

        file_path   = os.path.join(category_dir, file_name)
        save_result = self._write_file(file, file_path)
        if not save_result['success']:
            return save_result

        return {
            'success'  : True,
            'file_path': file_path,
            'file_url' : f"{self.base_url}/{category}/{file_name}",
            'file_name': file_name,
            'sequence' : sequence,
            'category' : category,
        }


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — image processing
    # ─────────────────────────────────────────────────────────────────────────

    def _compress_image_to_target(self, img, input_size_bytes=0):
        """
        Binary-search JPEG quality to land encoded size in 2–5 MB band.

        Rules:
          • Input ≤ 10 MB  → aim for midpoint ~3.5 MB
          • Input >  10 MB → prefer upper end, close to 5 MB
          • Naturally tiny (< 2 MB at q=95) → keep at q=95
          • Unstoppably large (> 5 MB at q=10) → use q=10

        Strategy:
          • Start at quality 85 — a good midpoint.
          • Binary-search between IMAGE_QUALITY_MIN and IMAGE_QUALITY_MAX.
          • Accept the first quality whose encoded size falls in [min, max].
          • If the image is naturally small (< min) even at quality max,
            store it at quality max (no upscaling).
          • If the image is enormous even at quality min, store at quality min
            (the best we can do without destroying the image).

        Returns:
            bytes: The final JPEG-encoded buffer.
        """
        min_bytes = int(IMAGE_TARGET_MIN_MB * 1024 * 1024)
        max_bytes = int(IMAGE_TARGET_MAX_MB * 1024 * 1024)

        lo      = IMAGE_QUALITY_MIN
        hi      = IMAGE_QUALITY_MAX
        best_buf = None

        while lo <= hi:
            mid = (lo + hi) // 2
            ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, mid])
            if not ok:
                break

            size = len(buf)

            if min_bytes <= size <= max_bytes:
                # Perfect — inside the target band
                return buf.tobytes()

            # Save this attempt as the best so far (closest to target)
            if best_buf is None:
                best_buf = buf
            else:
                prev_size = len(best_buf)
                # Prefer being inside the band; otherwise prefer closer to midpoint
                target_mid = (min_bytes + max_bytes) // 2
                if abs(size - target_mid) < abs(prev_size - target_mid):
                    best_buf = buf

            if size > max_bytes:
                hi = mid - 1   # Too big → lower quality
            else:
                lo = mid + 1   # Too small → raise quality

        # Return best approximation found
        if best_buf is not None:
            return best_buf.tobytes()

        # Last resort fallback
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buf.tobytes()


    def _save_image(self, file, category_dir, product_id, sequence, timestamp):
        """
        Convert ANY uploaded image to JPEG, compressed to 2–5 MB.
        Uses a custom temp directory and explicit handle management for Windows compatibility.
        """
        tmp_path = None
        try:
            # Define the custom temp directory path
            custom_temp_dir = r"D:\BE\Final Project\Farmo\ServerMedia\temp_uploads"
            if not os.path.exists(custom_temp_dir):
                os.makedirs(custom_temp_dir, exist_ok=True)

            ext = os.path.splitext(file.name)[1].lower()
        
            # Create temp file in the specific custom directory
            with tempfile.NamedTemporaryFile(dir=custom_temp_dir, delete=False, suffix=ext) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Read the image using OpenCV
            img = cv2.imread(tmp_path)
            if img is None:
                return {'success': False, 'error': 'Cannot read image — corrupt or unsupported format'}

            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id, 'img')

            file_name = f"{product_id}-img-{timestamp}-{sequence:03d}{IMAGE_SAVE_FORMAT}"
            file_path = os.path.join(category_dir, file_name)

            # Compress and get bytes
            jpeg_bytes = self._compress_image_to_target(img)

            # Write final file
            with open(file_path, 'wb') as f:
                f.write(jpeg_bytes)

            # CRITICAL FOR WINDOWS: Explicitly delete image object and collect garbage
            # to release the file handle held by cv2.imread
            del img
            import gc
            gc.collect()

            final_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            return {
                'success'   : True,
                'file_path' : file_path,
                'file_url'  : f"{self.base_url}/product/{file_name}",
                'file_name' : file_name,
                'sequence'  : sequence,
                'category'  : 'product',
                'size_mb'   : round(final_size_mb, 2),
                'converting': False,
            }

        except Exception as e:
            return {'success': False, 'error': f'Image processing failed: {str(e)}'}
        finally:
            self._safe_cleanupp(tmp_path)

    def _safe_cleanupp(self, path):
        """Helper to handle Windows file locks during cleanup."""
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except PermissionError:
                # Log the warning instead of crashing; 
                # BigFileTransferHandler will attempt its own cleanup
                print(f"Temporary file locked, cleanup deferred: {path}")

    def _save_profile_image(self, file, category_dir, file_purpose, timestamp):
        """
        Convert a profile picture or verification doc image to JPEG.
        Same compression pipeline as product images (2 to 5 MB target).
        """
        tmp_path = None
        try:
            ext = os.path.splitext(file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            img = cv2.imread(tmp_path)
            if img is None:
                return {'success': False, 'error': 'Cannot read image — corrupt or unsupported format'}

            file_name = f"{file_purpose}-{timestamp}{IMAGE_SAVE_FORMAT}"
            counter   = 1
            while os.path.exists(os.path.join(category_dir, file_name)):
                file_name = f"{file_purpose}-{timestamp}-{counter}{IMAGE_SAVE_FORMAT}"
                counter += 1

            file_path  = os.path.join(category_dir, file_name)
            jpeg_bytes = self._compress_image_to_target(img)

            with open(file_path, 'wb') as f:
                f.write(jpeg_bytes)

            final_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            return {
                'success'   : True,
                'file_path' : file_path,
                'file_url'  : f"{self.base_url}/profile/{file_name}",
                'file_name' : file_name,
                'sequence'  : None,
                'category'  : 'profile',
                'size_mb'   : round(final_size_mb, 2),
            }

        except Exception as e:
            return {'success': False, 'error': f'Profile image processing failed: {str(e)}'}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            try:
                file.seek(0)
            except Exception:
                pass


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — video processing
    # ─────────────────────────────────────────────────────────────────────────

    def _save_video(self, file, category_dir, product_id, sequence, timestamp):
        """
        Save raw video immediately (fast API response), then convert to
        720p MP4 in a background daemon thread.

        Input accepted  : any format, any size, up to FHD (1920×1080), ≤30s
        Output stored   : 1280×720 MP4 (H.264 + AAC), aspect-ratio preserved
                          with black letterbox/pillarbox padding if needed.
        """
        import shutil

        ext = os.path.splitext(file.name)[1].lower()

        if sequence is None:
            sequence = self._get_next_sequence(category_dir, product_id, 'vid')

        # Save raw file immediately so the API can respond fast
        raw_file_name = f"{product_id}-vid-{timestamp}-{sequence:03d}{ext}"
        raw_file_path = os.path.join(category_dir, raw_file_name)

        save_result = self._write_file(file, raw_file_path)
        if not save_result['success']:
            return save_result

        if not os.path.exists(raw_file_path):
            return {'success': False, 'error': 'Video was not saved successfully'}

        # Final filename is always .mp4
        final_file_name = f"{product_id}-vid-{timestamp}-{sequence:03d}.mp4"
        final_file_path = os.path.join(category_dir, final_file_name)

        needs_conversion = self._video_needs_conversion(raw_file_path)

        if not needs_conversion:
            # Already correct format and resolution — just rename if needed
            if ext != '.mp4':
                shutil.move(raw_file_path, final_file_path)
            else:
                final_file_path = raw_file_path
                final_file_name = raw_file_name

            return {
                'success'   : True,
                'file_path' : final_file_path,
                'file_url'  : f"{self.base_url}/product/{final_file_name}",
                'file_name' : final_file_name,
                'sequence'  : sequence,
                'category'  : 'product',
                'converting': False,
            }

        # Launch background conversion (daemon thread — auto-killed with process)
        thread = threading.Thread(
            target=self._convert_video_worker,
            args=(raw_file_path, final_file_path),
            daemon=True,
        )
        thread.start()

        return {
            'success'        : True,
            'file_path'      : raw_file_path,
            'file_url'       : f"{self.base_url}/product/{raw_file_name}",
            'file_name'      : raw_file_name,
            'final_file_name': final_file_name,
            'final_file_url' : f"{self.base_url}/product/{final_file_name}",
            'sequence'       : sequence,
            'category'       : 'product',
            'converting'     : True,
            'message'        : 'Video saved. Converting to 720p MP4 in background.',
        }


    def _video_needs_conversion(self, file_path):
        """Return True if the video is not already 720p MP4."""
        try:
            ext    = os.path.splitext(file_path)[1].lower()
            cap    = cv2.VideoCapture(file_path)
            width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if ext != '.mp4':
                return True
            if width > VIDEO_TARGET_WIDTH or height > VIDEO_TARGET_HEIGHT:
                return True
            return False
        except Exception:
            return True  # Can't determine — attempt conversion to be safe


    def _convert_video_worker(self, raw_path, output_path):
        """
        Background thread: convert to 720p MP4 via FFmpeg.

        • Scale to 1280×720, preserve aspect ratio
        • Pad with black bars if needed (letterbox / pillarbox)
        • H.264 + AAC, CRF 23, faststart for web delivery
        • Replaces raw file on success; leaves raw intact on failure
        """
        import subprocess
        import shutil

        try:
            if not shutil.which('ffmpeg'):
                print(f'[VideoConvert] ffmpeg not found. Raw file kept: {raw_path}')
                return

            tmp_output = output_path + '.tmp.mp4'

            cmd = [
                'ffmpeg', '-y',
                '-i', raw_path,
                '-vf', (
                    f'scale={VIDEO_TARGET_WIDTH}:{VIDEO_TARGET_HEIGHT}'
                    f':force_original_aspect_ratio=decrease,'
                    f'pad={VIDEO_TARGET_WIDTH}:{VIDEO_TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2'
                ),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-r', str(VIDEO_TARGET_FPS),
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                tmp_output,
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
            )

            if result.returncode == 0 and os.path.exists(tmp_output):
                os.replace(tmp_output, output_path)
                if os.path.exists(raw_path) and raw_path != output_path:
                    os.unlink(raw_path)
                print(f'[VideoConvert] Done: {output_path}')
            else:
                err = result.stderr.decode('utf-8', errors='replace')[-500:]
                print(f'[VideoConvert] FFmpeg failed ({result.returncode}): {err}')
                if os.path.exists(tmp_output):
                    os.unlink(tmp_output)

        except subprocess.TimeoutExpired:
            print(f'[VideoConvert] Timeout: {raw_path}')
        except Exception as e:
            print(f'[VideoConvert] Unexpected error: {e}')


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — validation
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_video_properties(self, file):
        """
        Validate video:
          • Duration  ≤ VIDEO_MAX_DURATION (30 s)
          • Resolution ≤ VIDEO_MAX_WIDTH × VIDEO_MAX_HEIGHT (1920 × 1080 FHD)
        Always resets the file pointer in the finally block.
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            cap         = cv2.VideoCapture(tmp_path)
            fps         = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if fps > 0:
                duration = frame_count / fps
                if duration > VIDEO_MAX_DURATION:
                    return {
                        'success': False,
                        'error'  : (
                            f'Video is {duration:.1f}s — '
                            f'maximum allowed is {VIDEO_MAX_DURATION}s.'
                        ),
                    }

            if width > VIDEO_MAX_WIDTH or height > VIDEO_MAX_HEIGHT:
                return {
                    'success': False,
                    'error'  : (
                        f'Video resolution {width}×{height} exceeds the '
                        f'{VIDEO_MAX_WIDTH}×{VIDEO_MAX_HEIGHT} (FHD) maximum.'
                    ),
                }

            return {
                'success' : True,
                'duration': round(frame_count / fps, 2) if fps > 0 else None,
                'width'   : width,
                'height'  : height,
            }

        except Exception:
            return {'success': True}  # Can't validate — allow upload
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            try:
                file.seek(0)
            except Exception:
                pass


    def _validate_file(self, file, allowed_extensions, max_size_mb):
        """Validate file presence, extension, and raw upload size."""
        if not file:
            return {'success': False, 'error': 'No file provided'}

        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return {
                'success': False,
                'error'  : f'Invalid file type. Allowed: {", ".join(allowed_extensions)}',
            }

        if max_size_mb is not None and file.size > max_size_mb * 1024 * 1024:
            return {'success': False, 'error': f'File size exceeds {max_size_mb}MB limit'}

        return {'success': True}


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _get_default_extensions(self, file_purpose):
        if file_purpose in ['profile-pic', 'verification-doc-front', 'verification-doc-back', 'img']:
            # Accept all common image formats — all will be converted to JPEG
            return ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif']
        if file_purpose == 'vid':
            return ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        return ['.jpg', '.jpeg', '.png', '.mp4']


    def _get_next_sequence(self, directory, product_id, file_purpose):
        """Determine next sequence number for product files."""
        if not os.path.exists(directory):
            return 1

        prefix  = f"{product_id}-{file_purpose}-"
        max_seq = 0

        try:
            for existing_file in os.listdir(directory):
                if not existing_file.startswith(prefix):
                    continue
                try:
                    remainder = existing_file[len(prefix):]
                    seq_part  = remainder.rsplit('-', 1)[-1]
                    seq_str   = os.path.splitext(seq_part)[0]
                    seq_num   = int(seq_str)
                    max_seq   = max(max_seq, seq_num)
                except (ValueError, IndexError):
                    continue
        except Exception:
            return 1

        return max_seq + 1


    def _write_file(self, file, file_path):
        """Write an uploaded file to disk chunk by chunk."""
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return {'success': True}
        except PermissionError as e:
            return {'success': False, 'error': f'Permission denied writing file: {str(e)}'}
        except IOError as e:
            return {'success': False, 'error': f'IO error writing file: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to save file: {str(e)}'}


    def _is_valid_category(self, category):
        return category in ['profile', 'product']


    def _is_safe_path(self, file_path):
        """Ensure the resolved path stays within the user's base directory."""
        return os.path.realpath(file_path).startswith(os.path.realpath(self.base_path))