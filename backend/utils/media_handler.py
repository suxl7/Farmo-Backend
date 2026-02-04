import os
import tempfile
import cv2
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ValidationError


class FileManager:
    """Manages file uploads and operations for users"""
    
    def __init__(self, user_id):
        """
        Initialize FileManager for a specific user
        
        Args:
            user_id: User ID for file organization
        """
        self.user_id = user_id
        self.base_path = os.path.join(settings.MEDIA_ROOT, 'Uploaded_Files', str(user_id))
        self.base_url = f"{settings.MEDIA_URL}Uploaded_Files/{user_id}"
    
    
    def save_profile_file(self, file, file_purpose, allowed_extensions=None, max_size_mb=1):
        """
        Save profile-related files
        
        Args:
            file: Uploaded file object
            file_purpose: 'profile-pic', 'verification-doc-front', 'verification-doc-back'
            allowed_extensions: List of allowed extensions
            max_size_mb: Maximum file size in MB
        
        Returns:
            dict: Result with success status and file info
        """
        return self._save_file(
            file=file,
            category='profile',
            file_purpose=file_purpose,
            allowed_extensions=allowed_extensions,
            max_size_mb=max_size_mb
        )
    
    
    def save_product_file(self, file, product_id, file_type, sequence=None, 
                         allowed_extensions=None, max_size_mb=5):
        """
        Save product-related files (images/videos)
        
        Args:
            file: Uploaded file object
            product_id: Product ID
            file_type: 'img' or 'vid'
            sequence: Sequence number (auto-generated if None)
            allowed_extensions: List of allowed extensions
            max_size_mb: Maximum file size in MB
        
        Returns:
            dict: Result with success status and file info
        """
        # Validate video duration if it's a video
        if file_type == 'vid':
            duration_check = self._validate_video_duration(file)
            if not duration_check['success']:
                return duration_check
        
        return self._save_file(
            file=file,
            category='product',
            file_purpose=file_type,
            product_id=product_id,
            sequence=sequence,
            allowed_extensions=allowed_extensions,
            max_size_mb=max_size_mb
        )
    
    
    def _save_file(self, file, category, file_purpose, product_id=None, 
                   sequence=None, allowed_extensions=None, max_size_mb=2):
        """
        Internal method to save files
        
        Args:
            file: Uploaded file object
            category: 'profile' or 'product'
            file_purpose: Type of file
            product_id: Product ID (required for products)
            sequence: Sequence number (auto for products)
            allowed_extensions: List of allowed extensions
            max_size_mb: Maximum file size in MB
        
        Returns:
            dict: {
                'success': True/False,
                'file_path': Absolute file path,
                'file_url': URL to access file,
                'file_name': Generated filename,
                'sequence': Sequence number (for products),
                'error': Error message (if failed)
            }
        """
        
        # Validate category
        if category not in ['profile', 'product']:
            return {
                'success': False,
                'error': 'Category must be "profile" or "product"'
            }
        
        # Validate product requirements
        if category == 'product' and not product_id:
            return {
                'success': False,
                'error': 'product_id is required for product files'
            }
        
        # Set default allowed extensions
        if allowed_extensions is None:
            allowed_extensions = self._get_default_extensions(file_purpose)
        
        # Validate file extension
        validation_result = self._validate_file(file, allowed_extensions, max_size_mb)
        if not validation_result['success']:
            return validation_result
        
        file_ext = os.path.splitext(file.name)[1].lower()
        
        # Create directory structure with proper error handling
        category_dir = os.path.join(self.base_path, category)
        
        try:
            # Create the directory with exist_ok=True
            os.makedirs(category_dir, exist_ok=True)
            
            # Verify directory was created successfully
            if not os.path.exists(category_dir):
                return {
                    'success': False,
                    'error': f'Failed to create directory: {category_dir}'
                }
            
            # Check if directory is writable
            if not os.access(category_dir, os.W_OK):
                return {
                    'success': False,
                    'error': f'Directory not writable: {category_dir}'
                }
                
        except PermissionError as e:
            return {
                'success': False,
                'error': f'Permission denied creating directory: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Directory creation failed: {str(e)}'
            }
        
        timestamp = datetime.now().strftime('%m%d%Y-%H%M%S')
        # Generate filename
        if category == 'profile':
            # Generate date string: MMDDYYYY (e.g., 02042026)
            # Format: MMDDYYYY_HHMMSS (e.g., 02042026_143005)
            
            
            # Construct filename: profile-pic_02042026.png
            file_name = f"{file_purpose}-{timestamp}{file_ext}"
            
            # Optional: Handle the rare case where two uploads happen on the same day
            # and you don't want to overwrite.
            counter = 1
            temp_name = file_name
            while os.path.exists(os.path.join(category_dir, temp_name)):
                temp_name = f"{file_purpose}-{timestamp}-{counter}{file_ext}"
                counter += 1
            file_name = temp_name
        else:  # product
            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id, file_purpose)
            file_name = f"{product_id}-{file_purpose}-{timestamp}-{sequence:03d}{file_ext}"
        
        # Full file path
        file_path = os.path.join(category_dir, file_name)
        
        # Check if file exists (for products)
        if os.path.exists(file_path) and category == 'product':
            return {
                'success': False,
                'error': f'File already exists: {file_name}'
            }
        
        # Save the file
        save_result = self._write_file(file, file_path)
        if not save_result['success']:
            return save_result
        
        # Verify file was actually written
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File was not saved successfully'
            }
        
        # Generate URL
        file_url = f"{self.base_url}/{category}/{file_name}"
        
        return {
            'success': True,
            'file_path': file_path,
            'file_url': file_url,
            'file_name': file_name,
            'sequence': sequence if category == 'product' else None,
            'category': category
        }
    
    
    def _validate_file(self, file, allowed_extensions, max_size_mb):
        """Validate file extension and size"""
        
        # Check if file exists
        if not file:
            return {
                'success': False,
                'error': 'No file provided'
            }
        
        # Check extension
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return {
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }
        
        # Check size
        max_size_bytes = max_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            return {
                'success': False,
                'error': f'File size exceeds {max_size_mb}MB limit'
            }
        
        return {'success': True}
    
    
    def _validate_video_duration(self, file, max_duration=30):
        """Validate video duration using OpenCV"""
        tmp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            # Check video duration
            cap = cv2.VideoCapture(tmp_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            
            if fps > 0:
                duration = frame_count / fps
                if duration > max_duration:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    return {
                        'success': False,
                        'error': f'Video duration exceeds {max_duration} seconds'
                    }
            
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            # Reset file pointer
            file.seek(0)
            return {'success': True}
            
        except Exception as e:
            # Clean up on error
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            # Reset file pointer
            file.seek(0)
            
            # Return success since we can't validate (better than blocking uploads)
            return {'success': True}
    
    
    def _get_default_extensions(self, file_purpose):
        """Get default allowed extensions based on file purpose"""
        
        if file_purpose in ['profile-pic', 'verification-doc-front', 'verification-doc-back', 'img']:
            return ['.jpg', '.jpeg', '.png', '.webp']
        elif file_purpose == 'vid':
            return ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        else:
            return ['.jpg', '.jpeg', '.png', '.mp4']
    
    
    def _get_next_sequence(self, directory, product_id, file_purpose):
        """Get next sequence number for product files"""
        
        if not os.path.exists(directory):
            return 1
        
        try:
            existing_files = os.listdir(directory)
            prefix = f"{product_id}-{file_purpose}-"
            
            max_seq = 0
            for existing_file in existing_files:
                if existing_file.startswith(prefix):
                    try:
                        # Extract sequence number from filename
                        seq_str = existing_file.replace(prefix, '').split('.')[0]
                        seq_num = int(seq_str)
                        max_seq = max(max_seq, seq_num)
                    except ValueError:
                        continue
            
            return max_seq + 1
            
        except Exception as e:
            # If we can't read directory, start from 1
            return 1
    
    
    def _write_file(self, file, file_path):
        """Write file to disk"""
        
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return {'success': True}
        except PermissionError as e:
            return {
                'success': False,
                'error': f'Permission denied writing file: {str(e)}'
            }
        except IOError as e:
            return {
                'success': False,
                'error': f'IO error writing file: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to save file: {str(e)}'
            }
    
    
    def delete_file(self, category, file_name):
        """
        Delete a specific file
        
        Args:
            category: 'profile' or 'product'
            file_name: Name of file to delete
        
        Returns:
            dict: {'success': True/False, 'error': Error message if failed}
        """
        
        file_path = os.path.join(self.base_path, category, file_name)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return {'success': True, 'message': 'File deleted successfully'}
            else:
                return {'success': False, 'error': 'File not found'}
        except PermissionError as e:
            return {'success': False, 'error': f'Permission denied: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    
    def delete_product_files(self, product_id):
        """
        Delete all files for a specific product
        
        Args:
            product_id: Product ID
        
        Returns:
            dict: {'success': True/False, 'deleted_count': int, 'errors': list}
        """
        
        product_dir = os.path.join(self.base_path, 'product')
        
        if not os.path.exists(product_dir):
            return {
                'success': True,
                'deleted_count': 0,
                'message': 'No product directory found'
            }
        
        deleted_count = 0
        errors = []
        
        try:
            files = os.listdir(product_dir)
            for file_name in files:
                if file_name.startswith(f"{product_id}-"):
                    result = self.delete_file('product', file_name)
                    if result['success']:
                        deleted_count += 1
                    else:
                        errors.append(f"{file_name}: {result['error']}")
            
            return {
                'success': len(errors) == 0,
                'deleted_count': deleted_count,
                'errors': errors if errors else None
            }
        except Exception as e:
            return {
                'success': False,
                'deleted_count': deleted_count,
                'errors': [str(e)]
            }
    
    
    def get_file_info(self, category, file_name):
        """
        Get information about a specific file
        
        Args:
            category: 'profile' or 'product'
            file_name: Name of the file
        
        Returns:
            dict: File information or error
        """
        
        file_path = os.path.join(self.base_path, category, file_name)
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found'
            }
        
        try:
            return {
                'success': True,
                'file_name': file_name,
                'file_path': file_path,
                'file_url': f"{self.base_url}/{category}/{file_name}",
                'size': os.path.getsize(file_path),
                'category': category
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error getting file info: {str(e)}'
            }
    
    
    def verify_setup(self):
        """
        Verify that the base directory structure can be created
        Useful for debugging directory creation issues
        
        Returns:
            dict: Status of directory setup
        """
        try:
            # Check if base MEDIA_ROOT exists
            if not os.path.exists(settings.MEDIA_ROOT):
                return {
                    'success': False,
                    'error': f'MEDIA_ROOT does not exist: {settings.MEDIA_ROOT}',
                    'tip': 'Create MEDIA_ROOT directory or check settings.py'
                }
            
            # Check if MEDIA_ROOT is writable
            if not os.access(settings.MEDIA_ROOT, os.W_OK):
                return {
                    'success': False,
                    'error': f'MEDIA_ROOT is not writable: {settings.MEDIA_ROOT}',
                    'tip': 'Check directory permissions'
                }
            
            # Try to create user directory
            os.makedirs(self.base_path, exist_ok=True)
            
            if not os.path.exists(self.base_path):
                return {
                    'success': False,
                    'error': f'Failed to create user directory: {self.base_path}'
                }
            
            # Try to create test subdirectories
            test_dirs = ['profile', 'product']
            for test_dir in test_dirs:
                test_path = os.path.join(self.base_path, test_dir)
                os.makedirs(test_path, exist_ok=True)
                if not os.path.exists(test_path):
                    return {
                        'success': False,
                        'error': f'Failed to create {test_dir} directory: {test_path}'
                    }
            
            return {
                'success': True,
                'base_path': self.base_path,
                'writable': os.access(self.base_path, os.W_OK),
                'media_root': settings.MEDIA_ROOT,
                'message': 'Directory structure verified successfully'
            }
            
        except PermissionError as e:
            return {
                'success': False,
                'error': f'Permission error: {str(e)}',
                'tip': 'Check folder permissions on the server'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Setup verification failed: {str(e)}'
            }
    
    
    def list_files(self, category=None):
        """
        List all files for this user
        
        Args:
            category: Optional - 'profile' or 'product' to filter
        
        Returns:
            dict: List of files with their info
        """
        try:
            files_list = []
            
            if category:
                categories = [category]
            else:
                categories = ['profile', 'product']
            
            for cat in categories:
                cat_dir = os.path.join(self.base_path, cat)
                
                if not os.path.exists(cat_dir):
                    continue
                
                for file_name in os.listdir(cat_dir):
                    file_path = os.path.join(cat_dir, file_name)
                    
                    if os.path.isfile(file_path):
                        files_list.append({
                            'file_name': file_name,
                            'category': cat,
                            'file_url': f"{self.base_url}/{cat}/{file_name}",
                            'size': os.path.getsize(file_path)
                        })
            
            return {
                'success': True,
                'files': files_list,
                'count': len(files_list)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error listing files: {str(e)}'
            }