import os
import uuid
import shutil
import base64
import mimetypes

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser, IsFarmer, IsAdmin
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.models import Users, Product, Verification
from backend.utils.media_handler import FileManager


##########################################################################################
#                             Big File UPLOAD Start
##########################################################################################

##########################################################################################
#                        Chunked Upload State (in-memory, per-process)
#
# For production, replace this dict with a Redis cache:
#   from django.core.cache import cache
#   cache.set(session_key, meta, timeout=3600)
#   meta = cache.get(session_key)
##########################################################################################

_upload_sessions = {}   # { upload_id: { meta... } }

VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif']

VIDEO_SINGLE_LIMIT = 25 * 1024 * 1024      # 25 MB
VIDEO_MAX_SIZE     = 200 * 1024 * 1024     # 200 MB

##########################################################################################
#                             Big File Upload — Chunked
#
#  Flow:
#   1. POST /upload/  { action: 'init',   ... }  →  returns upload_id
#   2. POST /upload/  { action: 'chunk',  ... }  →  returns chunk ack
#   3. POST /upload/  { action: 'finish', ... }  →  assembles file, returns file info
#   4. POST /upload/  { action: 'abort',  ... }  →  cleans up temp chunks
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
def big_file_upload(request):
    userid = request.headers.get('user-id')
    action = request.data.get('action')

    print(action)
    if not userid:
        return Response({'error': 'user-id is required'}, status=400)

    if action == 'init':
        return _upload_init(request, userid)
    if action == 'chunk':
        return _upload_chunk(request, userid)
    if action == 'finish':
        return _upload_finish(request, userid)
    if action == 'abort':
        return _upload_abort(request, userid)

    return Response({'error': 'Invalid action'}, status=400)


# ─────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────
def _upload_init(request, userid):
    file_name  = request.data.get('file_name')
    file_size  = int(request.data.get('file_size', 0))
    subject    = request.data.get('subject')
    ext        = os.path.splitext(file_name)[1].lower()

    # Profile picture: only images allowed
    if subject == 'PROFILE_PICTURE' and ext not in IMAGE_EXTS:
        return Response({'error': 'Profile picture must be an image file.'}, status=400)

    # Video size cap
    if ext in VIDEO_EXTS and file_size > VIDEO_MAX_SIZE:
        return Response({'error': 'Video exceeds 200MB limit'}, status=400)

    # Determine chunking mode
    is_image       = ext in IMAGE_EXTS
    is_small_video = ext in VIDEO_EXTS and file_size <= VIDEO_SINGLE_LIMIT

    if is_image or is_small_video or ext not in VIDEO_EXTS:
        total_chunks = 1
        mode = 'full'
    else:
        total_chunks = int(request.data.get('total_chunks', 1))
        mode = 'chunked'

    upload_id  = uuid.uuid4().hex
    chunks_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', upload_id)
    os.makedirs(chunks_dir, exist_ok=True)

    _upload_sessions[upload_id] = {
        'userid'      : userid,
        'subject'     : subject,
        'file_name'   : file_name,
        'file_size'   : file_size,
        'total_chunks': total_chunks,
        'received'    : set(),
        'chunks_dir'  : chunks_dir,
        'product_id'  : request.data.get('product_id'),
        'file_purpose': request.data.get('file_purpose'),
        'sequence'    : request.data.get('sequence'),
    }

    return Response({
        'upload_id'   : upload_id,
        'total_chunks': total_chunks,
        'mode'        : mode,
    })


# ─────────────────────────────────────────────────────────────
# CHUNK
# ─────────────────────────────────────────────────────────────
def _upload_chunk(request, userid):
    upload_id   = request.data.get('upload_id')
    chunk_index = int(request.data.get('chunk_index', 0))
    file        = request.FILES.get('file')

    session = _upload_sessions.get(upload_id)
    if not session or session['userid'] != userid:
        return Response({'error': 'Invalid session'}, status=403)

    chunk_path = os.path.join(session['chunks_dir'], f'chunk_{chunk_index:05d}')

    with open(chunk_path, 'wb') as f:
        for data in file.chunks():
            f.write(data)

    session['received'].add(chunk_index)
    return Response({'success': True, 'chunk': chunk_index})


# ─────────────────────────────────────────────────────────────
# FINISH
# ─────────────────────────────────────────────────────────────
def _upload_finish(request, userid):
    try:
        upload_id = request.data.get('upload_id')
        session   = _upload_sessions.get(upload_id)

        if not session:
            return Response({'error': 'Session expired or not found'}, status=400)

        total_chunks = session['total_chunks']
        received     = session['received']

        # 1. Verify all chunks received
        if len(received) < total_chunks:
            missing = list(set(range(total_chunks)) - received)
            return Response({'error': 'Incomplete upload', 'missing': missing}, status=400)

        # 2. Assemble file from chunks
        ext            = os.path.splitext(session['file_name'])[1].lower()
        assembled_path = os.path.join(session['chunks_dir'], f'final_build{ext}')

        with open(assembled_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(session['chunks_dir'], f'chunk_{i:05d}')
                with open(chunk_path, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)
            outfile.flush()
            os.fsync(outfile.fileno())  # Force write to disk (prevents 'moov' loss on videos)

        # 3. Save to DB — profile picture is handled directly (see _save_profile_picture_direct),
        #    product media goes through FileManager as before.
        result = _save_file_to_db(userid, session, assembled_path)

        # 4. Cleanup temp files
        _cleanup_session(upload_id)

        if not result.get('success'):
            return Response({'error': result.get('error')}, status=400)

        return Response(result)

    except Exception as e:
        return Response({'error': f'Assembly failed: {str(e)}'}, status=500)


# ─────────────────────────────────────────────────────────────
# SAVE TO DB
# ─────────────────────────────────────────────────────────────
def _save_file_to_db(userid, session, assembled_path):
    """
    Routes the assembled file to the correct save handler.
    Profile pictures are saved directly (bypassing the broken
    FileManager._save_profile_image path). Product media still
    goes through FileManager.save_product_file as before.
    """
    subject = session['subject']

    if subject == 'PROFILE_PICTURE':
        return _save_profile_picture_direct(userid, session, assembled_path)

    elif subject == 'PRODUCT_MEDIA':
        return _save_product_media(userid, session, assembled_path)

    return {'success': False, 'error': 'Unknown subject'}


# ─────────────────────────────────────────────────────────────
# PROFILE PICTURE — direct PIL save
# (bypasses FileManager._save_profile_image which is missing)
# ─────────────────────────────────────────────────────────────
def _save_profile_picture_direct(userid, session, assembled_path):
    """
    Compress the assembled image with PIL and save it to the
    user's profile directory.  Mirrors what FileManager would do
    internally via the missing _save_profile_image method.
    Targets 2–5 MB JPEG output via binary-search quality tuning.
    """
    from PIL import Image
    from backend.models import UsersProfile, UserActivity

    TARGET_MIN_MB = 2.0
    TARGET_MAX_MB = 5.0
    QUALITY_MAX   = 95
    QUALITY_MIN   = 10

    try:
        # ── Build destination path ────────────────────────────
        save_dir = os.path.join(settings.MEDIA_ROOT, 'Uploaded_Files', str(userid), 'profile')
        os.makedirs(save_dir, exist_ok=True)
        from datetime import datetime

        unique_name = f"profile-pic-{datetime.now().strftime('%d%m%Y_%H%M%S')}.jpg"
        dest_path    = os.path.join(save_dir, unique_name)
        # Relative URL stored in DB (no leading slash)
        relative_url = f"Uploaded_Files/{userid}/profile/{unique_name}"

        # ── Open and convert image ────────────────────────────
        with Image.open(assembled_path) as img:
            # Fix EXIF orientation (phones often store images sideways/upside-down)
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)

            # Convert to RGB so JPEG encoder is happy (handles RGBA / palette modes)
            if img.mode not in ('RGB',):
                img = img.convert('RGB')

            file_size_mb = os.path.getsize(assembled_path) / (1024 * 1024)

            # If the raw image is already in the target window, save at high quality
            if TARGET_MIN_MB <= file_size_mb <= TARGET_MAX_MB:
                img.save(dest_path, format='JPEG', quality=85, optimize=True)

            else:
                # Binary-search for a quality level that lands in [2, 5] MB
                lo, hi  = QUALITY_MIN, QUALITY_MAX
                quality = 75  # start in the middle

                for _ in range(10):  # at most 10 iterations — always converges
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=quality, optimize=True)
                    size_mb = buf.tell() / (1024 * 1024)

                    if size_mb < TARGET_MIN_MB:
                        lo = quality + 1
                    elif size_mb > TARGET_MAX_MB:
                        hi = quality - 1
                    else:
                        break  # within target window

                    if lo > hi:
                        break

                    quality = (lo + hi) // 2

                img.save(dest_path, format='JPEG', quality=quality, optimize=True)

        # ── Update DB ─────────────────────────────────────────
        user_obj = Users.objects.get(user_id=userid)
        profile  = UsersProfile.objects.get(profile_id=user_obj.profile_id.profile_id)

        # Delete old profile picture file if it exists (keep disk clean)
        if profile.profile_url:
            old_path = os.path.join(settings.MEDIA_ROOT, profile.profile_url)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass  # Non-fatal — carry on

        profile.profile_url = relative_url
        profile.save()

        # Log activity
        UserActivity.create_activity(user_obj, activity='UPDATE_PROFILE_PIC', discription='')

        return {'success': True, 'file_url': relative_url}

    except Exception as e:
        return {'success': False, 'error': f'Profile picture save failed: {str(e)}'}


# ─────────────────────────────────────────────────────────────
# PRODUCT MEDIA — via FileManager (unchanged logic)
# ─────────────────────────────────────────────────────────────
def _save_product_media(userid, session, assembled_path):
    fm         = FileManager(userid)
    product_id = session.get('product_id')

    if not product_id:
        return {'success': False, 'error': 'product_id is required'}

    try:
        product = Product.objects.get(p_id=product_id, user_id__user_id=userid)
    except Product.DoesNotExist:
        return {'success': False, 'error': 'Product not found'}

    # Determine media type from extension; allow file_purpose override
    ext        = os.path.splitext(session['file_name'])[1].lower()
    media_type = 'vid' if ext in VIDEO_EXTS else 'img'
    if session.get('file_purpose') in ('img', 'vid'):
        media_type = session['file_purpose']

    # Wrap assembled file for FileManager
    with open(assembled_path, 'rb') as f:
        django_file = InMemoryUploadedFile(
            f,
            None,
            session['file_name'],
            mimetypes.guess_type(session['file_name'])[0],
            os.path.getsize(assembled_path),
            None,
        )

        result = fm.save_product_file(
            file=django_file,
            product_id=product_id,
            file_type=media_type,
            sequence=session.get('sequence'),
        )

    if not result.get('success'):
        return {'success': False, 'error': result.get('error')}

    # Resolve sequence
    current_media = product.media_url
    if not isinstance(current_media, list):
        current_media = []

    sequence = session.get('sequence')
    if sequence is None:
        sequence = max((m.get('serial_no', 0) for m in current_media), default=0) + 1
    else:
        sequence = int(sequence)

    new_entry = {
        'serial_no' : sequence,
        'media_url' : result['file_url'],
        'media_type': media_type,
    }

    # Deduplicate by serial_no (handles retries) then append + sort
    current_media = [m for m in current_media if m.get('serial_no') != sequence]
    current_media.append(new_entry)
    current_media.sort(key=lambda x: x['serial_no'])

    product.media_url = current_media
    product.save()

    return {
        'success'   : True,
        'file_url'  : result['file_url'],
        'serial_no' : sequence,
        'media_type': media_type,
    }


# ─────────────────────────────────────────────────────────────
# ABORT
# ─────────────────────────────────────────────────────────────
def _upload_abort(request, userid):
    upload_id = request.data.get('upload_id')
    session   = _upload_sessions.get(upload_id)

    if session and session['userid'] == userid:
        _cleanup_session(upload_id)
        return Response({'message': 'Upload aborted'})

    return Response({'error': 'Session not found'}, status=404)


# ─────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────
def _cleanup_session(upload_id):
    session = _upload_sessions.pop(upload_id, None)
    if session:
        shutil.rmtree(session['chunks_dir'], ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# FILE WRAPPER
# ─────────────────────────────────────────────────────────────
class _AssembledFile:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.size = os.path.getsize(path)
        self._fh  = open(path, 'rb')

    def chunks(self, size=64 * 1024):
        self._fh.seek(0)
        while True:
            data = self._fh.read(size)
            if not data:
                break
            yield data

    def read(self, size=-1):
        return self._fh.read(size)

    def seek(self, pos):
        self._fh.seek(pos)

    def close(self):
        self._fh.close()


##########################################################################################
#                             Big File UPLOAD End
##########################################################################################

##########################################################################################
#                             Big File DOWNLOAD Start
##########################################################################################

@api_view(['POST'])
@permission_classes([AllowAny])
def big_file_download(request):
    userid     = request.headers.get('user-id')
    
    subject    = request.data.get('subject')
    product_id = request.data.get('product_id') if subject in ['PRODUCT_MEDIA','PRODUCT', 'product', 'product_media', 'productmedia', 'ProductMedia'] else None
    seq        = request.data.get('seq', 1)

    if subject == 'PROFILE_PICTURE':
        result, status= profile_pic_download(userid=userid)
    elif subject == 'PRODUCT_MEDIA':
        result, status= product_media_download(product_id=product_id, seq=seq)
    elif subject == 'USER_ID_VERIFICATION_MEDIA':
        result, status= user_id_verification_download(userid=userid, seq=seq)
    else:
        return Response({'error': 'Invalid or missing subject'}, status=400)

    return Response(result, status=status)


@api_view(['POST'])
@permission_classes([AllowAny, IsAdmin])
def big_file_download_v2(request):
    """
    New version of big_file_download with enhanced error handling and
    support for additional subjects like USER_ID_VERIFICATION_MEDIA.
    """
    userid     = request.data.get('user_id')
    
    subject    = request.data.get('subject')
    product_id = request.data.get('product_id') if subject in ['PRODUCT_MEDIA','PRODUCT', 'product', 'product_media', 'productmedia', 'ProductMedia'] else None
    seq        = request.data.get('seq', 1)

    if subject == 'PROFILE_PICTURE':
        result, status= profile_pic_download(userid=userid)
    elif subject == 'PRODUCT_MEDIA':
        result, status= product_media_download(userid=userid, product_id=product_id, seq=seq)
    elif subject == 'USER_ID_VERIFICATION_MEDIA':
        result, status= user_id_verification_download(userid=userid, seq=seq)
    else:
        return Response({'error': 'Invalid or missing subject'}, status=400)

    return Response(result, status=status)

##########################################################################################
#                             Big File DOWNLOAD End
##########################################################################################


# ─────────────────────────────────────────────────────────────
# PROFILE PICTURE DOWNLOAD  ← untouched from original
# ─────────────────────────────────────────────────────────────
def profile_pic_download(userid):
    """Download and base64-encode a user's profile picture."""

    try:
        user    = Users.objects.get(user_id=userid, profile_status='ACTIVATED')
        profile = user.profile_id
    except Users.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 1, 'seq': 1}, status.HTTP_404_NOT_FOUND

    if profile.profile_url:
        profile_url = settings.MEDIA_ROOT + '/' + profile.profile_url
    else:
        user_type = profile.user_type.lower()
        default_map = {
            'verifiedfarmer'  : 'pp-farmer.png',
            'farmer'          : 'pp-farmer.png',
            'verifiedconsumer': 'pp-consumer.png',
            'consumer'        : 'pp-consumer.png',
            'admin'           : 'pp-admin.png',
            'superadmin'      : 'pp-superadmin.png',
        }
        filename    = default_map.get(user_type, 'pp-guest.png')
        profile_url = f'backend/static/DefaultProfilePicture/{filename}'

    try:
        with open(profile_url, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type, _ = mimetypes.guess_type(profile_url)
    except FileNotFoundError:
        fallback = 'backend/static/DefaultProfilePicture/pp-guest.png'
        with open(fallback, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = 'image/png'

    return {
        'file'      : encoded_image,
        'mime_type' : mime_type,
        'media_type': 'img',
        'total'     : 1,
        'seq'       : 1,
    }, status.HTTP_200_OK




# ─────────────────────────────────────────────────────────────
# PRODUCT MEDIA DOWNLOAD  ← untouched from original
# ─────────────────────────────────────────────────────────────
def product_media_download(product_id, seq=1):
    """Download and base64-encode a product media file by sequence number."""

    try:
        product = Product.objects.get(p_id=product_id)
        media_list = product.media_url or []

        if not media_list:
            return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}, status.HTTP_404_NOT_FOUND

        # Find media by serial_no
        target_media = None
        for media in media_list:
            if media.get('serial_no') == int(seq):
                target_media = media
                break

        if not target_media:
            return {'file': None, 'mime_type': None, 'media_type': None, 'total': len(media_list), 'seq': 0}, status.HTTP_404_NOT_FOUND

        file_path = settings.MEDIA_ROOT + '/' + target_media.get('media_url', '')

        try:
            with open(file_path, 'rb') as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            mime_type, _ = mimetypes.guess_type(file_path)
        except FileNotFoundError:
            return {'file': None, 'mime_type': None, 'media_type': None, 'total': len(media_list), 'seq': 0}, status.HTTP_404_NOT_FOUND

        return {
            'file': encoded_image,
            'mime_type': mime_type,
            'media_type': target_media.get('media_type'),
            'total': len(media_list),
            'seq': target_media.get('serial_no'),
        }, status.HTTP_200_OK

    except Product.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}, status.HTTP_404_NOT_FOUND

    except Exception as e:
        return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}, status.HTTP_400_BAD_REQUEST




# ─────────────────────────────────────────────────────────────
# ID VERIFICATION DOWNLOAD  ← untouched from original
# ─────────────────────────────────────────────────────────────
def user_id_verification_download(userid, seq=1):
    """Download and base64-encode a user's ID verification image (front or back)."""

    try:
        user = Users.objects.get(user_id=userid)
        verification = Verification.objects.filter(user_id=user).latest('submission_date')

        seq = int(seq)
        if seq == 1:
            relative_path = verification.id_front
        elif seq == 2:
            relative_path = verification.id_back
        elif seq == 3:
            relative_path = verification.Selfie_with_id
        else:
            relative_path = verification.id_front  # fallback

        if not relative_path:
            return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 0, 'seq': seq}, status.HTTP_404_NOT_FOUND

        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        with open(file_path, 'rb') as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')

        mime_type, _ = mimetypes.guess_type(file_path)

        return {
            'file': encoded_file,
            'mime_type': mime_type,
            'media_type': 'img',
            'total': 3,
            'seq': seq,
        }, status.HTTP_200_OK

    except Users.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 0, 'seq': 0}, status.HTTP_404_NOT_FOUND

    except Verification.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 0, 'seq': 0}, status.HTTP_404_NOT_FOUND

    except FileNotFoundError:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 0, 'seq': 0}, status.HTTP_404_NOT_FOUND

    except Exception as e:
        print(f"[user_id_verification_download] Unexpected error: {e}")
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 0, 'seq': 0}, status.HTTP_400_BAD_REQUEST