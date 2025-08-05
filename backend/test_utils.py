"""
Test utilities for the backend application.
Provides helper functions and classes for testing.
"""

import json
import tempfile
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

User = get_user_model()

class TestDataHelper:
    """Helper class for creating test data"""
    
    @staticmethod
    def create_test_user(email='test@example.com', password='testpass123', **kwargs):
        """Create a test user with default or custom parameters"""
        return User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )
    
    @staticmethod
    def create_test_file(filename='test_file.pdf', content=b'Test file content'):
        """Create a test file for upload testing"""
        return SimpleUploadedFile(
            filename,
            content,
            content_type='application/pdf'
        )
    
    @staticmethod
    def create_mock_ai_response():
        """Create a mock AI service response"""
        return '''
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
    
    @staticmethod
    def create_test_portfolio_data():
        """Create test portfolio data"""
        return {
            'professional_summary': 'Experienced developer with 5 years of experience',
            'skills': ['Python', 'Django', 'React', 'JavaScript'],
            'work_experience': [
                {
                    'title': 'Senior Developer',
                    'company': 'Tech Corp',
                    'dates': '2020-2023',
                    'description': 'Led development team and built scalable applications'
                }
            ],
            'education': [
                {
                    'institution': 'University of Technology',
                    'degree': 'Master of Computer Science',
                    'dates': '2016-2018'
                }
            ],
            'template_choice': 'default'
        }

class APITestHelper:
    """Helper class for API testing"""
    
    @staticmethod
    def create_authenticated_client(user=None):
        """Create an authenticated API client"""
        client = APIClient()
        if user:
            client.force_authenticate(user=user)
        return client
    
    @staticmethod
    def assert_response_status(response, expected_status):
        """Assert response status with helpful error message"""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.data}"
    
    @staticmethod
    def assert_response_contains(response, key, value=None):
        """Assert response contains specific key and optionally value"""
        assert key in response.data, f"Key '{key}' not found in response: {response.data}"
        if value is not None:
            assert response.data[key] == value, \
                f"Expected {key}={value}, got {response.data[key]}"
    
    @staticmethod
    def assert_response_structure(response, expected_keys):
        """Assert response has expected structure"""
        response_keys = set(response.data.keys())
        expected_keys = set(expected_keys)
        missing_keys = expected_keys - response_keys
        extra_keys = response_keys - expected_keys
        
        assert not missing_keys, f"Missing keys in response: {missing_keys}"
        assert not extra_keys, f"Unexpected keys in response: {extra_keys}"

class MockHelper:
    """Helper class for creating mocks"""
    
    @staticmethod
    def mock_ai_service():
        """Create a mock for AI service"""
        return patch('apps.profiles.views.generate_portfolio_from_data')
    
    @staticmethod
    def mock_file_storage():
        """Create a mock for file storage"""
        return patch('apps.profiles.views.default_storage')
    
    @staticmethod
    def mock_gemini_api():
        """Create a mock for Gemini API"""
        return patch('apps.profiles.ai_service.genai')

class PerformanceHelper:
    """Helper class for performance testing"""
    
    @staticmethod
    def measure_time(func, *args, **kwargs):
        """Measure execution time of a function"""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def assert_performance(func, max_time, *args, **kwargs):
        """Assert function completes within specified time"""
        result, execution_time = PerformanceHelper.measure_time(func, *args, **kwargs)
        assert execution_time < max_time, \
            f"Function took {execution_time:.2f}s, expected less than {max_time}s"
        return result

class DataValidationHelper:
    """Helper class for data validation testing"""
    
    @staticmethod
    def validate_json_structure(data, expected_structure):
        """Validate JSON data structure"""
        def validate_recursive(data, structure):
            if isinstance(structure, dict):
                assert isinstance(data, dict), f"Expected dict, got {type(data)}"
                for key, expected_type in structure.items():
                    assert key in data, f"Missing key: {key}"
                    validate_recursive(data[key], expected_type)
            elif isinstance(structure, list):
                assert isinstance(data, list), f"Expected list, got {type(data)}"
                if data and isinstance(structure[0], (dict, list)):
                    for item in data:
                        validate_recursive(item, structure[0])
            else:
                assert isinstance(data, structure), \
                    f"Expected {structure}, got {type(data)}"
        
        validate_recursive(data, expected_structure)
    
    @staticmethod
    def validate_email_format(email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_linkedin_url(url):
        """Validate LinkedIn URL format"""
        return url.startswith('https://linkedin.com/in/') or \
               url.startswith('https://www.linkedin.com/in/')

class TestCleanupHelper:
    """Helper class for test cleanup"""
    
    @staticmethod
    def cleanup_test_files():
        """Clean up test files created during testing"""
        import shutil
        test_dirs = ['media/resumes', 'htmlcov', '__pycache__']
        for dir_name in test_dirs:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data from database"""
        from apps.users.models import CustomUser
        from apps.profiles.models import Profile
        from apps.portfolio.models import Portfolio
        
        # Delete test data in reverse dependency order
        Portfolio.objects.filter(slug__startswith='test').delete()
        Profile.objects.filter(linkedin_username__startswith='test').delete()
        CustomUser.objects.filter(email__startswith='test').delete()

# Convenience functions
def create_test_user(*args, **kwargs):
    """Create a test user"""
    return TestDataHelper.create_test_user(*args, **kwargs)

def create_authenticated_client(*args, **kwargs):
    """Create an authenticated API client"""
    return APITestHelper.create_authenticated_client(*args, **kwargs)

def mock_ai_service():
    """Create a mock for AI service"""
    return MockHelper.mock_ai_service()

def cleanup_test_environment():
    """Clean up test environment"""
    TestCleanupHelper.cleanup_test_files()
    TestCleanupHelper.cleanup_test_data() 