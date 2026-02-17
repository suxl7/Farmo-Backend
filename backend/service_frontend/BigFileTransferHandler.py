import os
import json
import hashlib

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
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
    """
    Chunked file upload endpoint.

    Headers:
        user-id: ID of the user uploading

    Actions
    -------
    init
        Body: {
            action       : 'init',
            subject      : 'PROFILE_PICTURE' | 'PRODUCT_MEDIA' | 'USER_ID_VERIFICATION_MEDIA',
            file_purpose : 'profile-pic' | 'verification-doc-front' | 'verification-doc-back'
                           | 'img' | 'vid',
            file_name    : 'original_filename.jpg',
            file_size    : <total bytes>,
            total_chunks : <int>,
            product_id   : <str>  (required for PRODUCT_MEDIA),
            sequence     : <int>  (optional, auto if omitted),
            checksum     : <md5 hex>  (optional, validated on finish if provided)
        }
        Returns: { upload_id, chunk_size }

    chunk
        Body (multipart): {
            action      : 'chunk',
            upload_id   : <str>,
            chunk_index : <int, 0-based>,
            file        : <binary chunk>
        }
        Returns: { upload_id, chunk_index, received }

    finish
        Body: {
            action    : 'finish',
            upload_id : <str>
        }
        Returns: { file_url, file_name, sequence, category, size }

    abort
        Body: { action: 'abort', upload_id: <str> }
        Returns: { message }
    """

    userid = request.headers.get('user-id') or request.data.get('user_id')
    action = request.data.get('action')

    if not userid:
        return Response({'error': 'user-id header is required'}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'init':
        return _upload_init(request, userid)
    elif action == 'chunk':
        return _upload_chunk(request, userid)
    elif action == 'finish':
        return _upload_finish(request, userid)
    elif action == 'abort':
        return _upload_abort(request, userid)
    else:
        return Response(
            {'error': 'Invalid action. Use: init | chunk | finish | abort'},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Action handlers
# ─────────────────────────────────────────────────────────────────────────────

def _upload_init(request, userid):
    """Register a new upload session and return an upload_id."""

    subject      = request.data.get('subject')
    file_purpose = request.data.get('file_purpose')
    file_name    = request.data.get('file_name')
    file_size    = request.data.get('file_size')
    total_chunks = request.data.get('total_chunks')
    product_id   = request.data.get('product_id')
    sequence     = request.data.get('sequence')
    checksum     = request.data.get('checksum')  # Optional MD5

    # ── Validation ──────────────────────────────────────────────────────────
    VALID_SUBJECTS = ['PROFILE_PICTURE', 'PRODUCT_MEDIA', 'USER_ID_VERIFICATION_MEDIA']
    if subject not in VALID_SUBJECTS:
        return Response({'error': f'subject must be one of: {", ".join(VALID_SUBJECTS)}'}, status=400)

    if not file_name:
        return Response({'error': 'file_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        file_size    = int(file_size)
        total_chunks = int(total_chunks)
        if file_size <= 0 or total_chunks <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'file_size and total_chunks must be positive integers'}, status=400)

    if subject == 'PRODUCT_MEDIA' and not product_id:
        return Response({'error': 'product_id is required for PRODUCT_MEDIA'}, status=400)

    # ── Determine size limits ────────────────────────────────────────────────
    ext = os.path.splitext(file_name)[1].lower()
    max_size_mb = 50 if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm'] else 10

    if file_size > max_size_mb * 1024 * 1024:
        return Response({'error': f'File too large. Max size: {max_size_mb}MB'}, status=400)

    # ── Create temp directory for chunks ────────────────────────────────────
    import uuid
    upload_id   = uuid.uuid4().hex
    chunks_dir  = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', upload_id)

    try:
        os.makedirs(chunks_dir, exist_ok=True)
    except Exception as e:
        return Response({'error': f'Failed to create upload session: {str(e)}'}, status=500)

    # ── Store session metadata ───────────────────────────────────────────────
    _upload_sessions[upload_id] = {
        'userid'       : userid,
        'subject'      : subject,
        'file_purpose' : file_purpose,
        'file_name'    : file_name,
        'file_size'    : file_size,
        'total_chunks' : total_chunks,
        'received'     : [],          # list of received chunk indices
        'product_id'   : product_id,
        'sequence'     : int(sequence) if sequence else None,
        'checksum'     : checksum,
        'chunks_dir'   : chunks_dir,
    }

    CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB recommended chunk size hint for client

    return Response({
        'upload_id'  : upload_id,
        'chunk_size' : CHUNK_SIZE,
        'total_chunks': total_chunks,
        'message'    : 'Upload session initialized',
    }, status=status.HTTP_200_OK)


def _upload_chunk(request, userid):
    """Receive and store a single chunk."""

    upload_id   = request.data.get('upload_id')
    chunk_index = request.data.get('chunk_index')
    chunk_file  = request.FILES.get('file')

    if not upload_id or chunk_index is None or not chunk_file:
        return Response({'error': 'upload_id, chunk_index, and file are required'}, status=400)

    # ── Session lookup ───────────────────────────────────────────────────────
    session = _upload_sessions.get(upload_id)
    if not session:
        return Response({'error': 'Upload session not found or expired'}, status=404)

    if session['userid'] != userid:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        chunk_index = int(chunk_index)
    except (TypeError, ValueError):
        return Response({'error': 'chunk_index must be an integer'}, status=400)

    if chunk_index < 0 or chunk_index >= session['total_chunks']:
        return Response({'error': f'chunk_index out of range (0–{session["total_chunks"] - 1})'}, status=400)

    if chunk_index in session['received']:
        # Idempotent — already received this chunk
        return Response({'upload_id': upload_id, 'chunk_index': chunk_index, 'received': True})

    # ── Write chunk to disk ──────────────────────────────────────────────────
    chunk_path = os.path.join(session['chunks_dir'], f'chunk_{chunk_index:05d}')
    try:
        with open(chunk_path, 'wb') as f:
            for data in chunk_file.chunks():
                f.write(data)
    except Exception as e:
        return Response({'error': f'Failed to write chunk: {str(e)}'}, status=500)

    session['received'].append(chunk_index)

    return Response({
        'upload_id'   : upload_id,
        'chunk_index' : chunk_index,
        'received'    : True,
        'progress'    : f"{len(session['received'])}/{session['total_chunks']}",
    }, status=status.HTTP_200_OK)


def _upload_finish(request, userid):
    """Assemble chunks, validate, and pass to FileManager."""

    upload_id = request.data.get('upload_id')

    if not upload_id:
        return Response({'error': 'upload_id is required'}, status=400)

    session = _upload_sessions.get(upload_id)
    if not session:
        return Response({'error': 'Upload session not found or expired'}, status=404)

    if session['userid'] != userid:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    # ── Check all chunks received ────────────────────────────────────────────
    total    = session['total_chunks']
    received = sorted(session['received'])
    expected = list(range(total))

    if received != expected:
        missing = sorted(set(expected) - set(received))
        return Response({'error': f'Missing chunks: {missing}'}, status=400)

    # ── Assemble chunks into a temp file ────────────────────────────────────
    import tempfile as _tempfile
    ext = os.path.splitext(session['file_name'])[1].lower()
    assembled_path = None

    try:
        with _tempfile.NamedTemporaryFile(delete=False, suffix=ext) as assembled:
            assembled_path = assembled.name
            md5 = hashlib.md5()

            for i in range(total):
                chunk_path = os.path.join(session['chunks_dir'], f'chunk_{i:05d}')
                with open(chunk_path, 'rb') as chunk_f:
                    data = chunk_f.read()
                    assembled.write(data)
                    md5.update(data)

        # ── Optional checksum validation ─────────────────────────────────────
        if session['checksum']:
            if md5.hexdigest() != session['checksum']:
                os.unlink(assembled_path)
                return Response({'error': 'Checksum mismatch — upload may be corrupted'}, status=400)

        # ── Wrap assembled file so FileManager can consume it ────────────────
        django_file = _AssembledFile(assembled_path, session['file_name'])

        fm = FileManager(userid)
        subject = session['subject']

        if subject == 'PROFILE_PICTURE':
            result = fm.save_profile_file(
                file=django_file,
                file_purpose=session['file_purpose'] or 'profile-pic',
            )
        elif subject == 'PRODUCT_MEDIA':
            result = fm.save_product_file(
                file=django_file,
                product_id=session['product_id'],
                file_type=session['file_purpose'] or 'img',
                sequence=session['sequence'],
            )
        elif subject == 'USER_ID_VERIFICATION_MEDIA':
            result = fm.save_profile_file(
                file=django_file,
                file_purpose=session['file_purpose'] or 'verification-doc-front',
                max_size_mb=10,
            )
        else:
            os.unlink(assembled_path)
            return Response({'error': 'Unknown subject'}, status=400)

        # ── Cleanup ──────────────────────────────────────────────────────────
        _cleanup_session(upload_id, assembled_path)

        if not result['success']:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message'   : 'File uploaded successfully',
            'file_url'  : result['file_url'],
            'file_name' : result['file_name'],
            'sequence'  : result.get('sequence'),
            'category'  : result.get('category'),
            'size'      : os.path.getsize(result['file_path']) if os.path.exists(result['file_path']) else None,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        _cleanup_session(upload_id, assembled_path)
        return Response({'error': f'Assembly failed: {str(e)}'}, status=500)


def _upload_abort(request, userid):
    """Cancel an in-progress upload and remove temp files."""

    upload_id = request.data.get('upload_id')
    if not upload_id:
        return Response({'error': 'upload_id is required'}, status=400)

    session = _upload_sessions.get(upload_id)
    if not session:
        return Response({'message': 'Session not found (may have already been cleaned up)'})

    if session['userid'] != userid:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    _cleanup_session(upload_id)
    return Response({'message': 'Upload aborted and temp files removed'})


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_session(upload_id, assembled_path=None):
    """Remove temp chunk directory and session entry."""
    import shutil
    session = _upload_sessions.pop(upload_id, None)
    if session and os.path.exists(session['chunks_dir']):
        shutil.rmtree(session['chunks_dir'], ignore_errors=True)
    if assembled_path and os.path.exists(assembled_path):
        try:
            os.unlink(assembled_path)
        except Exception:
            pass


class _AssembledFile:
    """
    Minimal file-like wrapper around an assembled temp file so that FileManager
    (which expects a Django UploadedFile interface) can consume it.
    """

    def __init__(self, path, original_name):
        self._path = path
        self.name  = original_name
        self.size  = os.path.getsize(path)
        self._fh   = open(path, 'rb')

    def chunks(self, chunk_size=64 * 1024):
        self._fh.seek(0)
        while True:
            data = self._fh.read(chunk_size)
            if not data:
                break
            yield data

    def seek(self, pos):
        self._fh.seek(pos)

    def read(self, size=-1):
        return self._fh.read(size) if size >= 0 else self._fh.read()

    def close(self):
        self._fh.close()

    def __del__(self):
        try:
            self._fh.close()
        except Exception:
            pass

##########################################################################################
#                             Big File UPLOAD End
########################################################################################

##########################################################################################
#                             Big File DOWNLOAD Start
##########################################################################################


@api_view(['POST'])
@permission_classes([AllowAny])
def big_file_download(request):
    userid = request.headers.get('user-id')
    subject = request.data.get('subject')
    product_id = request.data.get('product_id') if subject == 'PRODUCT_MEDIA' else None
    seq = request.data.get('seq', 1)

    if subject == 'PROFILE_PICTURE':
        result = profile_pic_download(userid=userid)
    elif subject == 'PRODUCT_MEDIA':
        result = product_media_download(userid=userid, product_id=product_id, seq=seq)
    elif subject == 'USER_ID_VERIFICATION_MEDIA':
        result = user_id_verification_download(userid=userid, seq=seq)
    else:
        return Response({'error': 'Invalid or missing subject'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result, status=status.HTTP_200_OK)

##########################################################################################
#                            Big File DOWNLOAD End
##########################################################################################

import base64
import mimetypes


def profile_pic_download(userid):
    """Download and base64-encode a user's profile picture."""

    try:
        user = Users.objects.get(user_id=userid, profile_status='ACTIVATED')
        profile = user.profile_id
    except Users.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 1, 'seq': 1}

    # Determine the profile picture path
    if profile.profile_url:
        profile_url = os.path.join(settings.MEDIA_ROOT, profile.profile_url)
    else:
        user_type = profile.user_type.lower()
        default_map = {
            'verifiedfarmer': 'pp-farmer.png',
            'farmer':         'pp-farmer.png',
            'verifiedconsumer': 'pp-consumer.png',
            'consumer':       'pp-consumer.png',
            'admin':          'pp-admin.png',
            'superadmin':     'pp-superadmin.png',
        }
        filename = default_map.get(user_type, 'pp-guest.png')
        profile_url = f'backend/static/DefaultProfilePicture/{filename}'

    # Encode to base64, fall back to guest picture if file is missing
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
        'file': encoded_image,
        'mime_type': mime_type,
        'media_type': 'img',
        'total': 1,
        'seq': 1,
    }

####################################################################################################################
####################################################################################################################

def product_media_download(userid, product_id, seq=1):
    """Download and base64-encode a product media file by sequence number."""

    try:
        product = Product.objects.get(pid=product_id, user_id__user_id=userid)
        media_list = product.media_url  # Expected: list of dicts with 'serial_no' and 'media_url'

        target_media = next((m for m in media_list if m['serial_no'] == int(seq)), None)

        if not target_media:
            return {'file': None, 'mime_type': None, 'media_type': None, 'total': len(media_list), 'seq': 0}

        file_path = os.path.join(settings.MEDIA_ROOT, target_media['media_url'])

        with open(file_path, 'rb') as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')

        mime_type, _ = mimetypes.guess_type(file_path)

        return {
            'file': encoded_file,
            'mime_type': mime_type,
            'media_type': target_media['media_type'],
            'total': len(media_list),
            'seq': target_media['serial_no'],
        }

    except Product.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}
    except FileNotFoundError:
        return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}
    except Exception as e:
        # Unexpected error — log and return safe response
        print(f"[product_pic_download] Unexpected error: {e}")
        return {'file': None, 'mime_type': None, 'media_type': None, 'total': 0, 'seq': 0}


####################################################################################################################
####################################################################################################################

def user_id_verification_download(userid, seq=1):
    """Download and base64-encode a user's ID verification image (front or back)."""

    try:
        verification = Verification.objects.filter(user_id=userid).latest('submission_date')

        seq = int(seq)
        if seq == 1:
            relative_path = verification.id_front
        elif seq == 2:
            relative_path = verification.id_back
        else:
            relative_path = verification.id_front  # fallback

        if not relative_path:
            return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 2, 'seq': seq}

        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        with open(file_path, 'rb') as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')

        mime_type, _ = mimetypes.guess_type(file_path)

        return {
            'file': encoded_file,
            'mime_type': mime_type,
            'media_type': 'img',
            'total': 2,
            'seq': seq,
        }

    except Verification.DoesNotExist:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 2, 'seq': 0}
    except FileNotFoundError:
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 2, 'seq': 0}
    except Exception as e:
        print(f"[user_id_verification_download] Unexpected error: {e}")
        return {'file': None, 'mime_type': None, 'media_type': 'img', 'total': 2, 'seq': 0}