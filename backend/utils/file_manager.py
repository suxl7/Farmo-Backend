import os
from django.conf import settings
from django.core.exceptions import ValidationError
from pathlib import Path


class FileManager:
    """Manages file uploads and operations for users"""
    
    def __init__(self, user_id):
        """
        Initialize FileManager for a specific user
        
        Args:
            user_id: User ID for file organization
        """
        self.user_id = user_id
        self.base_path = os.path.join(settings.MEDIA_ROOT, 'Uploaded_Files', user_id)
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
        
        # Create directory
        category_dir = os.path.join(self.base_path, category)
        os.makedirs(category_dir, exist_ok=True)
        
        # Generate filename
        if category == 'profile':
            file_name = f"{file_purpose}{file_ext}"
        else:  # product
            if sequence is None:
                sequence = self._get_next_sequence(category_dir, product_id, file_purpose)
            file_name = f"{product_id}-{file_purpose}-{sequence:03d}{file_ext}"
        
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
        
        existing_files = os.listdir(directory)
        prefix = f"{product_id}-{file_purpose}-"
        
        max_seq = 0
        for existing_file in existing_files:
            if existing_file.startswith(prefix):
                try:
                    seq_str = existing_file.replace(prefix, '').split('.')[0]
                    seq_num = int(seq_str)
                    max_seq = max(max_seq, seq_num)
                except ValueError:
                    continue
        
        return max_seq + 1
    
    
    def _write_file(self, file, file_path):
        """Write file to disk"""
        
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return {'success': True}
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
        
        return {
            'success': True,
            'file_name': file_name,
            'file_path': file_path,
            'file_url': f"{self.base_url}/{category}/{file_name}",
            'size': os.path.getsize(file_path),
            'category': category
        }