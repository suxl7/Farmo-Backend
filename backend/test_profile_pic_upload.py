import os
import shutil
import tempfile
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from backend.models import Users, UsersProfile

class ProfilePictureUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.temp_media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.temp_media_root

        self.user_data = {
            'user_id': 'testuser',
            'password': 'testpassword',
            'f_name': 'Test',
            'l_name': 'User',
            'user_type': 'farmer',
            'phone': '1234567890',
        }

    def tearDown(self):
        shutil.rmtree(self.temp_media_root)

    def test_profile_picture_upload(self):
        # Create a dummy image file
        image_name = 'test_image.png'
        image_path = os.path.join(self.temp_media_root, image_name)
        with open(image_path, 'wb') as f:
            f.write(b'test image data')

        with open(image_path, 'rb') as f:
            response = self.client.post(reverse('register'), {
                **self.user_data,
                'profile_picture': f
            })

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Users.objects.filter(user_id=self.user_data['user_id']).exists())
        user_profile = UsersProfile.objects.get(f_name=self.user_data['f_name'])
        self.assertIsNotNone(user_profile.profile_url)

        # Check if the file was uploaded
        profile_id = user_profile.profile_id
        file_ext = os.path.splitext(image_name)[1]
        expected_filename = f"{profile_id}{file_ext}"
        expected_filepath = os.path.join(settings.MEDIA_ROOT, 'profiles', expected_filename)
        self.assertTrue(os.path.exists(expected_filepath))