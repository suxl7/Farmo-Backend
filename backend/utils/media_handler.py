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
        self.custom_temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
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

        Args:
            category  : 'profile' or 'product'
            file_name : Name of the file to delete

        Returns:
            dict: Result with success status
        """
        if not self._is_valid_category(category):
            return {'success': False, 'error': 'Category must be "profile" or "product"'}

        file_path = os.path.join(self.base_path, category, file_name)

        if not self._is_path_safe(file_path):
            return {'success': False, 'error': 'Invalid file path'}

        if not os.path.exists(file_path):
            return {'success': False, 'error': 'File does not exist'}

        try:
            os.remove(file_path)
            return {'success': True, 'message': f'File {file_name} deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to delete file: {str(e)}'}


    def list_files(self, category):
        """
        List all files in a category.

        Args:
            category: 'profile' or 'product'

        Returns:
            dict: Result with success status and file list
        """
        if not self._is_valid_category(category):
            return {'success': False, 'error': 'Category must be "profile" or "product"'}

        category_dir = os.path.join(self.base_path, category)
        
        if not os.path.exists(category_dir):
            return {'success': True, 'files': []}

        try:
            files = []
            for file_name in os.listdir(category_dir):
                file_path = os.path.join(category_dir, file_name)
                if os.path.isfile(file_path):
                    files.append({
                        'name': file_name,
                        'size': os.path.getsize(file_path),
                        'url': f"{self.base_url}/{category}/{file_name}"
                    })
            return {'success': True, 'files': files}
        except Exception as e:
            return {'success': False, 'error': f'Failed to list files: {str(e)}'}


    def verify_setup(self):
        """
        Verify that the directory structure is correctly set up.
        
        Returns:
            dict: Result with success status and diagnostic info
        """
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
        os.makedirs(category_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        # Route: profile images
        if category == 'profile' and file_purpose in [
            'profile-pic', 'verification-doc-front', 'verification-doc-back'
        ]:
            return self._save_profile_image(file, category_dir, file_purpose, timestamp)

        # Route: product images
        if category == 'product' and file_purpose == 'img':
            return self._save_product_image(file, category_dir, product_id, sequence, timestamp)

        # Route: product videos
        if category == 'product' and file_purpose == 'vid':
            return self._save_video(file, category_dir, product_id, sequence, timestamp)

        # Fallback for unrecognized purposes
        return {'success': False, 'error': f'Unrecognized file_purpose: {file_purpose}'}


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — validation
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_file(self, file, allowed_extensions, max_size_mb):
        """Basic size & extension checks."""
        if not file:
            return {'success': False, 'error': 'No file provided'}

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed_extensions:
            return {
                'success': False,
                'error'  : f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }

        size_mb = file.size / (1024 * 1024)
        if size_mb > max_size_mb:
            return {
                'success': False,
                'error'  : f'File size {size_mb:.2f} MB exceeds limit of {max_size_mb} MB'
            }

        return {'success': True}


    def _validate_video_properties(self, file):
        """
        Validate video duration ≤30s and resolution ≤FHD.
        Works by saving to a temp file, then reading with cv2.VideoCapture.
        """
        tmp_path = None
        try:
            ext = os.path.splitext(file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=self.custom_temp_dir) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                return {'success': False, 'error': 'Cannot open video file'}

            fps    = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            duration = frames / fps if fps > 0 else 0

            if duration > VIDEO_MAX_DURATION:
                return {
                    'success': False,
                    'error'  : f'Video duration {duration:.1f}s exceeds {VIDEO_MAX_DURATION}s limit'
                }

            if width > VIDEO_MAX_WIDTH or height > VIDEO_MAX_HEIGHT:
                return {
                    'success': False,
                    'error'  : f'Video resolution {width}×{height} exceeds FHD ({VIDEO_MAX_WIDTH}×{VIDEO_MAX_HEIGHT})'
                }

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': f'Video validation failed: {str(e)}'}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    # Log the warning instead of crashing; 
                    # BigFileTransferHandler will attempt its own cleanup
                    print(f"Temporary file locked, cleanup deferred: {tmp_path}")

    

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
        tmp_path = None
        try:
            # 1. Save raw video to temp
            ext = os.path.splitext(file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=self.custom_temp_dir) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # 2. Determine sequence
            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id)

            # 3. Save raw immediately (so API responds fast)
            raw_name = f"{product_id}-vid-{sequence}-{timestamp}{ext}"
            raw_path = os.path.join(category_dir, raw_name)

            import shutil
            shutil.copy2(tmp_path, raw_path)

            # 4. Background conversion
            final_name = f"{product_id}-vid-{sequence}-{timestamp}.mp4"
            final_path = os.path.join(category_dir, final_name)

            thread = threading.Thread(
                target=self._convert_video_background,
                args=(tmp_path, final_path, raw_path),
                daemon=True
            )
            thread.start()

            # 5. Return immediately
            return {
                'success'    : True,
                'file_path'  : final_path,
                'file_url'   : f"{self.base_url}/product/{final_name}",
                'file_name'  : final_name,
                'sequence'   : sequence,
                'category'   : 'product',
                'converting' : True,
                'message'    : 'Video uploaded; converting to 720p MP4 in background',
            }

        except Exception as e:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return {'success': False, 'error': f'Video save failed: {str(e)}'}


    def _convert_video_background(self, src_path, dest_path, raw_path):
        """
        Background thread: convert video to 720p MP4 with aspect-ratio preserved.
        Deletes raw file when done.
        """
        try:
            cap = cv2.VideoCapture(src_path)
            if not cap.isOpened():
                print(f"[Video conversion] Cannot open {src_path}")
                return

            in_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            in_h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps   = cap.get(cv2.CAP_PROP_FPS) or VIDEO_TARGET_FPS

            # Compute scale to fit inside 1280×720, preserving aspect ratio
            scale = min(VIDEO_TARGET_WIDTH / in_w, VIDEO_TARGET_HEIGHT / in_h)
            new_w = int(in_w * scale)
            new_h = int(in_h * scale)

            # Padding to center the scaled frame in 1280×720 canvas
            pad_x = (VIDEO_TARGET_WIDTH  - new_w) // 2
            pad_y = (VIDEO_TARGET_HEIGHT - new_h) // 2

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(dest_path, fourcc, fps, (VIDEO_TARGET_WIDTH, VIDEO_TARGET_HEIGHT))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize frame
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                # Create black canvas and place resized frame in center
                canvas = cv2.copyMakeBorder(
                    resized,
                    top=pad_y,
                    bottom=VIDEO_TARGET_HEIGHT - new_h - pad_y,
                    left=pad_x,
                    right=VIDEO_TARGET_WIDTH - new_w - pad_x,
                    borderType=cv2.BORDER_CONSTANT,
                    value=(0, 0, 0)
                )

                out.write(canvas)

            cap.release()
            out.release()

            # Delete raw file
            if os.path.exists(raw_path):
                os.unlink(raw_path)
            if os.path.exists(src_path):
                os.unlink(src_path)

            print(f"[Video conversion] Complete: {dest_path}")

        except Exception as e:
            print(f"[Video conversion] Error: {str(e)}")


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — product image processing
    # ─────────────────────────────────────────────────────────────────────────

    def _save_product_image(self, file, category_dir, product_id, sequence, timestamp):
        """
        Convert product image to JPEG with adaptive compression.
        Target: 2-5 MB for normal images, up to 5 MB for large inputs (>10 MB).
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

            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id)

            file_name = f"{product_id}-img-{sequence}-{timestamp}{IMAGE_SAVE_FORMAT}"
            counter   = 1
            while os.path.exists(os.path.join(category_dir, file_name)):
                file_name = f"{product_id}-img-{sequence}-{timestamp}-{counter}{IMAGE_SAVE_FORMAT}"
                counter += 1

            file_path  = os.path.join(category_dir, file_name)
            jpeg_bytes = self._compress_image_to_target(img)

            with open(file_path, 'wb') as f:
                f.write(jpeg_bytes)

            final_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            return {
                'success'   : True,
                'file_path' : file_path,
                'file_url'  : f"{self.base_url}/product/{file_name}",
                'file_name' : file_name,
                'sequence'  : sequence,
                'category'  : 'product',
                'size_mb'   : round(final_size_mb, 2),
            }

        except Exception as e:
            return {'success': False, 'error': f'Product image processing failed: {str(e)}'}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            try:
                file.seek(0)
            except Exception:
                pass


    def _compress_image_to_target(self, img):
        """
        Compress image to JPEG targeting 2-5 MB range using binary search.
        For large inputs (>10 MB assumed), prefer upper bound (5 MB).
        """
        # Try max quality first
        _, buf = cv2.imencode(IMAGE_SAVE_FORMAT, img, [cv2.IMWRITE_JPEG_QUALITY, IMAGE_QUALITY_MAX])
        size_mb = len(buf) / (1024 * 1024)

        # Already small enough? done
        if IMAGE_TARGET_MIN_MB <= size_mb <= IMAGE_TARGET_MAX_MB:
            return buf.tobytes()

        # Too small at max quality? just return it
        if size_mb < IMAGE_TARGET_MIN_MB:
            return buf.tobytes()

        # Large input? prefer upper bound (5 MB)
        if size_mb > IMAGE_LARGE_THRESHOLD_MB:
            target = IMAGE_LARGE_PREFER_MB
        else:
            target = (IMAGE_TARGET_MIN_MB + IMAGE_TARGET_MAX_MB) / 2

        # Binary search for quality
        low, high = IMAGE_QUALITY_MIN, IMAGE_QUALITY_MAX
        best_buf = buf

        for _ in range(10):  # max iterations
            mid = (low + high) // 2
            _, buf = cv2.imencode(IMAGE_SAVE_FORMAT, img, [cv2.IMWRITE_JPEG_QUALITY, mid])
            size_mb = len(buf) / (1024 * 1024)

            if abs(size_mb - target) < 0.1:  # close enough
                best_buf = buf
                break

            if size_mb > target:
                high = mid - 1
            else:
                low = mid + 1

            best_buf = buf

        return best_buf.tobytes()


    # ─────────────────────────────────────────────────────────────────────────
    # Internal — utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _get_next_sequence(self, category_dir, product_id):
        """Find the next available sequence number for a product."""
        if not os.path.exists(category_dir):
            return 1

        max_seq = 0
        prefix = f"{product_id}-"
        for filename in os.listdir(category_dir):
            if filename.startswith(prefix):
                parts = filename.split('-')
                if len(parts) >= 3:
                    try:
                        seq = int(parts[2])
                        max_seq = max(max_seq, seq)
                    except ValueError:
                        continue
        return max_seq + 1


    def _get_default_extensions(self, file_purpose):
        """Return default allowed extensions based on file purpose."""
        if file_purpose in ['profile-pic', 'verification-doc-front', 'verification-doc-back']:
            return ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif']
        if file_purpose == 'img':
            return ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif']
        if file_purpose == 'vid':
            return ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        return []


    def _is_valid_category(self, category):
        """Check if category is valid."""
        return category in ['profile', 'product']


    def _is_path_safe(self, file_path):
        """Check if the file path is within the allowed base path (security)."""
        return os.path.realpath(file_path).startswith(os.path.realpath(self.base_path))