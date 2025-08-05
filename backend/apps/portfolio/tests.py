from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Portfolio
from .serializers import PortfolioSerializer
from apps.profiles.models import Profile
import json

class PortfolioModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
    
    def test_portfolio_creation(self):
        """Test creating a portfolio with all required fields"""
        portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='Experienced software engineer',
            skills=['Python', 'Django', 'React'],
            work_experience=[
                {
                    'title': 'Software Engineer',
                    'company': 'Tech Corp',
                    'dates': '2020-2023',
                    'description': 'Developed web applications'
                }
            ],
            education=[
                {
                    'institution': 'University',
                    'degree': 'Computer Science',
                    'dates': '2016-2020'
                }
            ],
            template_choice='default'
        )
        
        self.assertEqual(portfolio.slug, 'john-doe-123')
        self.assertEqual(portfolio.professional_summary, 'Experienced software engineer')
        self.assertEqual(len(portfolio.skills), 3)
        self.assertEqual(len(portfolio.work_experience), 1)
        self.assertEqual(len(portfolio.education), 1)
        self.assertEqual(portfolio.template_choice, 'default')
    
    def test_portfolio_string_representation(self):
        """Test portfolio string representation"""
        portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='',
            skills=[],
            work_experience=[],
            education=[],
            template_choice='default'
        )
        self.assertEqual(str(portfolio), 'Portfolio for john-doe-123')
    
    def test_portfolio_unique_slug(self):
        """Test that portfolio slug must be unique"""
        Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='',
            skills=[],
            work_experience=[],
            education=[],
            template_choice='default'
        )
        
        # Create another profile and try to create portfolio with same slug
        user2 = self.User.objects.create_user(
            email='user2@example.com',
            username='user2'
        )
        profile2 = Profile.objects.create(
            user=user2,
            linkedin_url='https://linkedin.com/in/jane-doe-456/',
            linkedin_username='jane-doe-456'
        )
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            Portfolio.objects.create(
                profile=profile2,
                slug='john-doe-123',  # Same slug
                professional_summary='',
                skills=[],
                work_experience=[],
                education=[],
                template_choice='default'
            )
    
    def test_portfolio_json_fields(self):
        """Test that JSON fields work correctly"""
        skills = ['Python', 'Django', 'React', 'JavaScript']
        work_experience = [
            {
                'title': 'Senior Developer',
                'company': 'Tech Corp',
                'dates': '2020-2023',
                'description': 'Led development team'
            },
            {
                'title': 'Junior Developer',
                'company': 'Startup Inc',
                'dates': '2018-2020',
                'description': 'Built web applications'
            }
        ]
        education = [
            {
                'institution': 'University of Technology',
                'degree': 'Master of Computer Science',
                'dates': '2016-2018'
            }
        ]
        
        portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='test-portfolio',
            professional_summary='Experienced developer',
            skills=skills,
            work_experience=work_experience,
            education=education,
            template_choice='modern'
        )
        
        # Refresh from database
        portfolio.refresh_from_db()
        
        self.assertEqual(portfolio.skills, skills)
        self.assertEqual(portfolio.work_experience, work_experience)
        self.assertEqual(portfolio.education, education)

class PortfolioSerializerTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        self.portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='Experienced developer',
            skills=['Python', 'Django'],
            work_experience=[],
            education=[],
            template_choice='default'
        )
    
    def test_serializer_valid_data(self):
        """Test serializer with valid portfolio data"""
        serializer = PortfolioSerializer(self.portfolio)
        data = serializer.data
        
        self.assertEqual(data['slug'], 'john-doe-123')
        self.assertEqual(data['professional_summary'], 'Experienced developer')
        self.assertEqual(data['skills'], ['Python', 'Django'])
        self.assertEqual(data['template_choice'], 'default')
        self.assertIn('id', data)
    
    def test_serializer_all_fields(self):
        """Test that serializer includes all model fields"""
        serializer = PortfolioSerializer(self.portfolio)
        data = serializer.data
        
        expected_fields = {
            'id', 'profile', 'slug', 'professional_summary',
            'skills', 'work_experience', 'education', 'template_choice'
        }
        self.assertEqual(set(data.keys()), expected_fields)

class PortfolioViewTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
        self.portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='Experienced developer',
            skills=['Python', 'Django'],
            work_experience=[],
            education=[],
            template_choice='default'
        )
    
    def test_portfolio_me_get_authenticated(self):
        """Test getting user's own portfolio when authenticated"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/portfolio/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'john-doe-123')
        self.assertEqual(response.data['professional_summary'], 'Experienced developer')
    
    def test_portfolio_me_get_unauthenticated(self):
        """Test getting user's own portfolio when not authenticated"""
        response = self.client.get('/api/portfolio/me/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_portfolio_me_put_authenticated(self):
        """Test updating user's own portfolio when authenticated"""
        self.client.force_authenticate(user=self.user)
        update_data = {
            'professional_summary': 'Updated summary',
            'skills': ['Python', 'Django', 'React']
        }
        response = self.client.put('/api/portfolio/me/', update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['professional_summary'], 'Updated summary')
        self.assertEqual(len(response.data['skills']), 3)
    
    def test_portfolio_me_put_invalid_data(self):
        """Test updating portfolio with invalid data"""
        self.client.force_authenticate(user=self.user)
        update_data = {
            'slug': '',  # Invalid empty slug
        }
        response = self.client.put('/api/portfolio/me/', update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_portfolio_public_get_existing(self):
        """Test getting public portfolio by slug"""
        response = self.client.get('/api/portfolio/public/john-doe-123/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'john-doe-123')
    
    def test_portfolio_public_get_nonexistent(self):
        """Test getting non-existent public portfolio"""
        response = self.client.get('/api/portfolio/public/nonexistent-slug/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_portfolio_public_get_unauthenticated(self):
        """Test that public portfolio endpoint works without authentication"""
        response = self.client.get('/api/portfolio/public/john-doe-123/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class PortfolioIntegrationTest(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.client = APIClient()
        self.user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            linkedin_url='https://linkedin.com/in/john-doe-123/',
            linkedin_username='john-doe-123'
        )
    
    def test_complete_portfolio_workflow(self):
        """Test complete portfolio creation and management workflow"""
        # Create portfolio
        portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='john-doe-123',
            professional_summary='Initial summary',
            skills=['Python'],
            work_experience=[],
            education=[],
            template_choice='default'
        )
        
        # Test GET request
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/portfolio/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['professional_summary'], 'Initial summary')
        
        # Test PUT request
        update_data = {
            'professional_summary': 'Updated summary',
            'skills': ['Python', 'Django', 'React'],
            'work_experience': [
                {
                    'title': 'Developer',
                    'company': 'Tech Corp',
                    'dates': '2020-2023',
                    'description': 'Built applications'
                }
            ]
        }
        response = self.client.put('/api/portfolio/me/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['professional_summary'], 'Updated summary')
        self.assertEqual(len(response.data['skills']), 3)
        self.assertEqual(len(response.data['work_experience']), 1)
        
        # Test public access
        response = self.client.get('/api/portfolio/public/john-doe-123/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['professional_summary'], 'Updated summary')
    
    def test_portfolio_data_validation(self):
        """Test portfolio data validation"""
        portfolio = Portfolio.objects.create(
            profile=self.profile,
            slug='test-portfolio',
            professional_summary='',
            skills=[],
            work_experience=[],
            education=[],
            template_choice='default'
        )
        
        # Test valid JSON data
        valid_data = {
            'skills': ['Python', 'Django'],
            'work_experience': [
                {
                    'title': 'Developer',
                    'company': 'Tech Corp',
                    'dates': '2020-2023',
                    'description': 'Built applications'
                }
            ]
        }
        
        self.client.force_authenticate(user=self.user)
        response = self.client.put('/api/portfolio/me/', valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test invalid JSON data
        invalid_data = {
            'skills': 'not a list',  # Should be a list
            'work_experience': 'not a list'  # Should be a list
        }
        response = self.client.put('/api/portfolio/me/', invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
