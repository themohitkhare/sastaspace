import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()

class UserFactory(DjangoModelFactory):
    """Factory for creating test users"""
    
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
    is_staff = False
    is_superuser = False

class SuperUserFactory(DjangoModelFactory):
    """Factory for creating test superusers"""
    
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'admin{n}@example.com')
    username = factory.Sequence(lambda n: f'admin{n}')
    password = factory.PostGenerationMethodCall('set_password', 'adminpass123')
    is_active = True
    is_staff = True
    is_superuser = True

class InactiveUserFactory(DjangoModelFactory):
    """Factory for creating inactive test users"""
    
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'inactive{n}@example.com')
    username = factory.Sequence(lambda n: f'inactive{n}')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = False
    is_staff = False
    is_superuser = False 