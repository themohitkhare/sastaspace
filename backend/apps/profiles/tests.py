from django.test import TestCase
from .models import Profile
from django.contrib.auth import get_user_model

class ProfileModelTest(TestCase):
    def test_linkedin_username_extraction(self):
        user = get_user_model().objects.create(email='test@example.com', username='testuser')
        url = 'https://linkedin.com/in/john-doe-123/'
        profile = Profile.objects.create(user=user, linkedin_url=url, linkedin_username='john-doe-123')
        self.assertEqual(profile.linkedin_username, 'john-doe-123')
