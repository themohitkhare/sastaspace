from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import CustomUser
from .serializers import CustomUserSerializer
import json

class CustomUserModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
    
    def test_user_creation_with_email(self):
        """Test creating a user with email and password"""
        user = self.User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_creation_with_username(self):
        """Test creating a user with username"""
        user = self.User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
    
    def test_superuser_creation(self):
        """Test creating a superuser"""
        superuser = self.User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
    
    def test_user_creation_without_email(self):
        """Test that user creation without email raises error"""
        with self.assertRaises(ValueError):
            self.User.objects.create_user(email='', password='testpass123')
    
    def test_user_creation_without_password(self):
        """Test that user creation without password raises error"""
        with self.assertRaises(ValueError):
            self.User.objects.create_user(email='test@example.com', password='')
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = self.User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'test@example.com')

class CustomUserSerializerTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }
    
    def test_serializer_valid_data(self):
        """Test serializer with valid data"""
        user = self.User.objects.create_user(**self.user_data)
        serializer = CustomUserSerializer(user)
        data = serializer.data
        
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['username'], 'testuser')
        self.assertIn('id', data)
    
    def test_serializer_fields(self):
        """Test that serializer includes correct fields"""
        user = self.User.objects.create_user(**self.user_data)
        serializer = CustomUserSerializer(user)
        data = serializer.data
        
        expected_fields = {'id', 'email', 'username'}
        self.assertEqual(set(data.keys()), expected_fields)

class CustomUserViewTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('user-list')  # Assuming this URL pattern exists
    
    def test_user_list_view_authenticated(self):
        """Test user list view when authenticated"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'test@example.com')
    
    def test_user_list_view_unauthenticated(self):
        """Test user list view when not authenticated"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_list_view_multiple_users(self):
        """Test user list view with multiple users"""
        self.User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

class CustomUserIntegrationTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
    
    def test_user_creation_and_retrieval(self):
        """Test complete user creation and retrieval flow"""
        # Create user
        user = self.User.objects.create_user(
            email='integration@example.com',
            password='testpass123'
        )
        
        # Authenticate and retrieve
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/users/')  # Adjust URL as needed
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('integration@example.com', [u['email'] for u in response.data])
    
    def test_user_password_validation(self):
        """Test user password validation"""
        # Test weak password
        with self.assertRaises(ValueError):
            self.User.objects.create_user(
                email='test@example.com',
                password='123'  # Too short
            )
        
        # Test valid password
        user = self.User.objects.create_user(
            email='test@example.com',
            password='validpass123'
        )
        self.assertTrue(user.check_password('validpass123'))
