import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .factories import UserFactory, SuperUserFactory, InactiveUserFactory

User = get_user_model()

@pytest.mark.unit
class UserEdgeCaseTest(TestCase):
    """Test edge cases for user model and operations"""
    
    def test_user_creation_with_special_characters(self):
        """Test user creation with special characters in email"""
        user = User.objects.create_user(
            email='test+tag@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test+tag@example.com')
    
    def test_user_creation_with_very_long_email(self):
        """Test user creation with very long email address"""
        long_email = 'a' * 50 + '@' + 'b' * 50 + '.com'
        user = User.objects.create_user(
            email=long_email,
            password='testpass123'
        )
        self.assertEqual(user.email, long_email)
    
    def test_user_creation_with_unicode_username(self):
        """Test user creation with unicode characters in username"""
        user = User.objects.create_user(
            username='usér_námé',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'usér_námé')
    
    def test_user_password_with_special_characters(self):
        """Test user creation with special characters in password"""
        special_password = 'P@ssw0rd!@#$%^&*()'
        user = User.objects.create_user(
            email='test@example.com',
            password=special_password
        )
        self.assertTrue(user.check_password(special_password))
    
    def test_user_creation_with_empty_username(self):
        """Test user creation with empty username"""
        user = User.objects.create_user(
            email='test@example.com',
            username='',
            password='testpass123'
        )
        self.assertEqual(user.username, '')
    
    def test_user_creation_with_very_long_username(self):
        """Test user creation with very long username"""
        long_username = 'a' * 150  # Django's default max_length
        user = User.objects.create_user(
            email='test@example.com',
            username=long_username,
            password='testpass123'
        )
        self.assertEqual(user.username, long_username)

@pytest.mark.unit
class UserErrorHandlingTest(TestCase):
    """Test error handling for user operations"""
    
    def test_user_creation_with_invalid_email_format(self):
        """Test user creation with invalid email format"""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'test@',
            'test@.com',
            'test..test@example.com'
        ]
        
        for email in invalid_emails:
            with self.assertRaises(Exception):
                User.objects.create_user(
                    email=email,
                    password='testpass123'
                )
    
    def test_user_creation_with_duplicate_email(self):
        """Test user creation with duplicate email"""
        User.objects.create_user(
            email='duplicate@example.com',
            password='testpass123'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='duplicate@example.com',
                password='testpass123'
            )
    
    def test_user_creation_with_duplicate_username(self):
        """Test user creation with duplicate username"""
        User.objects.create_user(
            email='test1@example.com',
            username='duplicate_user',
            password='testpass123'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='test2@example.com',
                username='duplicate_user',
                password='testpass123'
            )
    
    def test_user_creation_with_null_email(self):
        """Test user creation with null email"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email=None,
                password='testpass123'
            )
    
    def test_user_creation_with_empty_password(self):
        """Test user creation with empty password"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='test@example.com',
                password=''
            )

@pytest.mark.unit
class UserFactoryTest(TestCase):
    """Test user factories for generating test data"""
    
    def test_user_factory_creates_valid_user(self):
        """Test that UserFactory creates valid users"""
        user = UserFactory()
        self.assertIsNotNone(user.email)
        self.assertIsNotNone(user.username)
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_superuser_factory_creates_valid_superuser(self):
        """Test that SuperUserFactory creates valid superusers"""
        superuser = SuperUserFactory()
        self.assertIsNotNone(superuser.email)
        self.assertIsNotNone(superuser.username)
        self.assertTrue(superuser.check_password('adminpass123'))
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
    
    def test_inactive_user_factory_creates_inactive_user(self):
        """Test that InactiveUserFactory creates inactive users"""
        user = InactiveUserFactory()
        self.assertIsNotNone(user.email)
        self.assertIsNotNone(user.username)
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_factory_creates_unique_users(self):
        """Test that UserFactory creates unique users"""
        users = [UserFactory() for _ in range(5)]
        emails = [user.email for user in users]
        usernames = [user.username for user in users]
        
        self.assertEqual(len(emails), len(set(emails)))
        self.assertEqual(len(usernames), len(set(usernames)))

@pytest.mark.performance
class UserPerformanceTest(TestCase):
    """Test performance aspects of user operations"""
    
    def test_bulk_user_creation_performance(self):
        """Test performance of bulk user creation"""
        import time
        
        start_time = time.time()
        users = [UserFactory() for _ in range(100)]
        end_time = time.time()
        
        self.assertEqual(len(users), 100)
        self.assertLess(end_time - start_time, 5.0)  # Should complete within 5 seconds
    
    def test_user_query_performance(self):
        """Test performance of user queries"""
        import time
        
        # Create test users
        [UserFactory() for _ in range(50)]
        
        # Test query performance
        start_time = time.time()
        users = User.objects.all()
        end_time = time.time()
        
        self.assertGreater(len(users), 50)
        self.assertLess(end_time - start_time, 1.0)  # Should complete within 1 second
    
    def test_user_authentication_performance(self):
        """Test performance of user authentication"""
        import time
        
        user = UserFactory()
        
        # Test authentication performance
        start_time = time.time()
        for _ in range(100):
            user.check_password('testpass123')
        end_time = time.time()
        
        self.assertLess(end_time - start_time, 1.0)  # Should complete within 1 second

@pytest.mark.integration
class UserIntegrationEdgeCaseTest(APITestCase):
    """Test integration edge cases for user API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
    
    def test_api_with_malformed_json(self):
        """Test API with malformed JSON data"""
        self.client.force_authenticate(user=self.user)
        
        # Test with malformed JSON
        response = self.client.post(
            '/api/users/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_api_with_very_large_payload(self):
        """Test API with very large payload"""
        self.client.force_authenticate(user=self.user)
        
        # Create a very large payload
        large_data = {
            'email': 'test@example.com',
            'username': 'a' * 10000,  # Very long username
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/api/users/',
            data=large_data,
            format='json'
        )
        
        # Should either succeed or fail gracefully
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_api_with_special_headers(self):
        """Test API with special headers"""
        self.client.force_authenticate(user=self.user)
        
        # Test with special headers
        response = self.client.get(
            '/api/users/',
            HTTP_X_FORWARDED_FOR='192.168.1.1',
            HTTP_USER_AGENT='TestBot/1.0'
        )
        
        # Should handle special headers gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])
    
    def test_api_concurrent_requests(self):
        """Test API with concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            self.client.force_authenticate(user=self.user)
            response = self.client.get('/api/users/')
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should complete successfully
        self.assertEqual(len(results), 5)
        for status_code in results:
            self.assertIn(status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]) 