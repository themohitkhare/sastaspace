from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer
from .ai_service import generate_portfolio_from_data
from apps.portfolio.models import Portfolio
import json
import os
from unittest.mock import patch, MagicMock

class ProfileModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
    
    def test_profile_creation(self):
        """Test creating a profile with all required fields"""
        profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123',
            resume_text='Experienced software engineer with 5 years of experience.'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.linkedin_url, 'https://linkedin.com/in/john-doe-123/')
        self.assertEqual(profile.linkedin_username, 'john-doe-123')
        self.assertEqual(profile.resume_text, 'Experienced software engineer with 5 years of experience.')
        self.assertIsNone(profile.ai_analysis_cache)
    
    def test_profile_string_representation(self):
        """Test profile string representation"""
        profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        self.assertEqual(str(profile), 'Profile of test@example.com')
    
    def test_profile_unique_linkedin_url(self):
        """Test that profile linkedin_url must be unique"""
        Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        
        # Create another user and try to create profile with same linkedin_url
        user2 = self.User.objects.create_user(
            email='user2@example.com',
            username='user2'
        )
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            Profile.objects.create(
                user=user2,
                linkedin_url='https://linkedin.com/in/john-doe-123/',  # Same URL
                linkedin_username='jane-doe-456'
            )
    
    def test_profile_unique_linkedin_username(self):
        """Test that profile linkedin_username must be unique"""
        Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        
        # Create another user and try to create profile with same linkedin_username
        user2 = self.User.objects.create_user(
            email='user2@example.com',
            username='user2'
        )
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            Profile.objects.create(
                user=user2,
                linkedin_url='https://linkedin.com/in/jane-doe-456/',
                linkedin_username='john-doe-123'  # Same username
            )
    
    def test_profile_ai_analysis_cache(self):
        """Test that AI analysis cache works correctly"""
        ai_cache = {
            'professional_summary': 'Experienced developer',
            'skills': ['Python', 'Django'],
            'formatted_experience': [],
            'formatted_education': [],
            'actionable_feedback': []
        }
        
        profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123',
            ai_analysis_cache=ai_cache
        )
        
        # Refresh from database
        profile.refresh_from_db()
        
        self.assertEqual(profile.ai_analysis_cache, ai_cache)
    
    def test_profile_file_upload(self):
        """Test profile with resume file upload"""
        # Create a mock file
        file_content = b'Mock resume content'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123',
            resume_file=resume_file
        )
        
        self.assertIsNotNone(profile.resume_file)
        self.assertTrue(profile.resume_file.name.startswith('resumes/'))

class ProfileSerializerTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123',
            resume_text='Experienced developer'
        )
    
    def test_serializer_valid_data(self):
        """Test serializer with valid profile data"""
        serializer = ProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['linkedin_url'], 'https://linkedin.com/in/john-doe-123/')
        self.assertEqual(data['linkedin_username'], 'john-doe-123')
        self.assertEqual(data['resume_text'], 'Experienced developer')
        self.assertIn('id', data)
        self.assertIn('user', data)
    
    def test_serializer_all_fields(self):
        """Test that serializer includes all model fields"""
        serializer = ProfileSerializer(self.profile)
        data = serializer.data
        
        expected_fields = {
            'id', 'user', 'linkedin_url', 'linkedin_username',
            'resume_file', 'resume_text', 'ai_analysis_cache'
        }
        self.assertEqual(set(data.keys()), expected_fields)

class AIServiceTest(TestCase):
    @patch('apps.profiles.ai_service.genai')
    def test_generate_portfolio_from_data(self, mock_genai):
        """Test AI service portfolio generation"""
        # Mock the AI response
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "professional_summary": "Experienced software engineer with expertise in Python and Django.",
            "skills": ["Python", "Django", "React", "JavaScript"],
            "formatted_experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Corp",
                    "dates": "2020-2023",
                    "description": "Led development team and built scalable applications"
                }
            ],
            "formatted_education": [
                {
                    "institution": "University of Technology",
                    "degree": "Master of Computer Science",
                    "dates": "2016-2018"
                }
            ],
            "actionable_feedback": [
                "Add more quantifiable achievements",
                "Include specific technologies used",
                "Highlight leadership experience"
            ]
        }
        '''
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test the function
        resume_text = "Experienced software engineer with 5 years of experience in Python and Django."
        linkedin_data = "Senior Developer at Tech Corp"
        
        result = generate_portfolio_from_data(resume_text, linkedin_data)
        
        # Verify the result contains expected content
        self.assertIn('professional_summary', result)
        self.assertIn('skills', result)
        self.assertIn('formatted_experience', result)
        self.assertIn('formatted_education', result)
        self.assertIn('actionable_feedback', result)
        
        # Verify the AI model was called correctly
        mock_genai.GenerativeModel.assert_called_once_with('gemini-pro')
        mock_model.generate_content.assert_called_once()
    
    @patch('apps.profiles.ai_service.genai')
    def test_generate_portfolio_from_data_empty_input(self, mock_genai):
        """Test AI service with empty input"""
        mock_response = MagicMock()
        mock_response.text = '{"professional_summary": "", "skills": [], "formatted_experience": [], "formatted_education": [], "actionable_feedback": []}'
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = generate_portfolio_from_data("", "")
        
        self.assertIsInstance(result, str)
        mock_model.generate_content.assert_called_once()

class ProfileViewTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
    
    @patch('apps.profiles.views.generate_portfolio_from_data')
    @patch('apps.profiles.views.default_storage')
    def test_onboard_view_success(self, mock_storage, mock_ai_service):
        """Test successful onboarding process"""
        # Mock AI service response
        mock_ai_response = '''
        {
            "professional_summary": "Experienced developer",
            "skills": ["Python", "Django"],
            "formatted_experience": [],
            "formatted_education": [],
            "actionable_feedback": []
        }
        '''
        mock_ai_service.return_value = mock_ai_response
        
        # Mock file storage
        mock_storage.save.return_value = 'resumes/test_resume.pdf'
        
        # Create test file
        file_content = b'Mock resume content'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'resume_file': resume_file,
            'linkedin_url': 'https://linkedin.com/in/john-doe-123/'
        }
        
        response = self.client.post('/api/profiles/onboard/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('slug', response.data)
        self.assertEqual(response.data['slug'], 'john-doe-123')
        
        # Verify profile was created
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.linkedin_url, 'https://linkedin.com/in/john-doe-123/')
        self.assertEqual(profile.linkedin_username, 'john-doe-123')
        
        # Verify portfolio was created
        portfolio = Portfolio.objects.get(profile=profile)
        self.assertEqual(portfolio.slug, 'john-doe-123')
    
    def test_onboard_view_missing_resume(self):
        """Test onboarding without resume file"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'linkedin_url': 'https://linkedin.com/in/john-doe-123/'
        }
        
        response = self.client.post('/api/profiles/onboard/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_onboard_view_missing_linkedin_url(self):
        """Test onboarding without LinkedIn URL"""
        self.client.force_authenticate(user=self.user)
        
        file_content = b'Mock resume content'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        data = {
            'resume_file': resume_file
        }
        
        response = self.client.post('/api/profiles/onboard/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_onboard_view_unauthenticated(self):
        """Test onboarding without authentication"""
        file_content = b'Mock resume content'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        data = {
            'resume_file': resume_file,
            'linkedin_url': 'https://linkedin.com/in/john-doe-123/'
        }
        
        response = self.client.post('/api/profiles/onboard/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.profiles.views.generate_portfolio_from_data')
    @patch('apps.profiles.views.default_storage')
    def test_onboard_view_linkedin_username_extraction(self, mock_storage, mock_ai_service):
        """Test LinkedIn username extraction from URL"""
        mock_ai_service.return_value = '{"professional_summary": "", "skills": [], "formatted_experience": [], "formatted_education": [], "actionable_feedback": []}'
        mock_storage.save.return_value = 'resumes/test_resume.pdf'
        
        file_content = b'Mock resume content'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Test different LinkedIn URL formats
        test_urls = [
            'https://linkedin.com/in/john-doe-123/',
            'https://linkedin.com/in/jane-doe-456',
            'https://www.linkedin.com/in/tech-leader-789/',
            'https://linkedin.com/in/simple-name'
        ]
        
        expected_usernames = [
            'john-doe-123',
            'jane-doe-456',
            'tech-leader-789',
            'simple-name'
        ]
        
        for i, url in enumerate(test_urls):
            data = {
                'resume_file': resume_file,
                'linkedin_url': url
            }
            
            response = self.client.post('/api/profiles/onboard/', data, format='multipart')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['slug'], expected_usernames[i])

class ProfileIntegrationTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
    
    @patch('apps.profiles.views.generate_portfolio_from_data')
    @patch('apps.profiles.views.default_storage')
    def test_complete_onboarding_workflow(self, mock_storage, mock_ai_service):
        """Test complete onboarding workflow"""
        # Mock AI service
        mock_ai_response = '''
        {
            "professional_summary": "Experienced software engineer with expertise in Python and Django.",
            "skills": ["Python", "Django", "React"],
            "formatted_experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Corp",
                    "dates": "2020-2023",
                    "description": "Led development team"
                }
            ],
            "formatted_education": [
                {
                    "institution": "University of Technology",
                    "degree": "Master of Computer Science",
                    "dates": "2016-2018"
                }
            ],
            "actionable_feedback": [
                "Add more quantifiable achievements",
                "Include specific technologies used"
            ]
        }
        '''
        mock_ai_service.return_value = mock_ai_response
        mock_storage.save.return_value = 'resumes/test_resume.pdf'
        
        # Create test file
        file_content = b'Experienced software engineer with 5 years of experience in Python and Django.'
        resume_file = SimpleUploadedFile(
            'resume.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Perform onboarding
        data = {
            'resume_file': resume_file,
            'linkedin_url': 'https://linkedin.com/in/john-doe-123/'
        }
        
        response = self.client.post('/api/profiles/onboard/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify profile creation
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.linkedin_url, 'https://linkedin.com/in/john-doe-123/')
        self.assertEqual(profile.linkedin_username, 'john-doe-123')
        self.assertIsNotNone(profile.ai_analysis_cache)
        
        # Verify portfolio creation
        portfolio = Portfolio.objects.get(profile=profile)
        self.assertEqual(portfolio.slug, 'john-doe-123')
        self.assertEqual(portfolio.template_choice, 'default')
        
        # Test accessing the created portfolio
        portfolio_response = self.client.get('/api/portfolio/me/')
        self.assertEqual(portfolio_response.status_code, status.HTTP_200_OK)
        self.assertEqual(portfolio_response.data['slug'], 'john-doe-123')
        
        # Test public access
        public_response = self.client.get('/api/portfolio/public/john-doe-123/')
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
    
    def test_profile_data_validation(self):
        """Test profile data validation"""
        # Test invalid LinkedIn URL
        profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        
        # Test valid profile data
        self.assertEqual(profile.linkedin_username, 'john-doe-123')
        self.assertTrue(profile.linkedin_url.startswith('https://linkedin.com/in/'))
        
        # Test invalid LinkedIn URL format
        with self.assertRaises(Exception):
            Profile.objects.create(
                user=self.user,
                linkedin_url='invalid-url',
                linkedin_username='invalid-username'
            )
