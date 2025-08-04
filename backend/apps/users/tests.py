from django.test import TestCase
from .models import CustomUser

class CustomUserTest(TestCase):
    def test_user_creation(self):
        user = CustomUser.objects.create_user(email='test@example.com', password='testpass')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass'))
