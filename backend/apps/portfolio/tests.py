from django.test import TestCase
from .models import Portfolio
from apps.profiles.models import Profile
from django.contrib.auth import get_user_model

class PortfolioModelTest(TestCase):
    def test_portfolio_slug(self):
        user = get_user_model().objects.create(email='test@example.com', username='testuser')
        profile = Profile.objects.create(user=user, linkedin_url='https://linkedin.com/in/john-doe-123/', linkedin_username='john-doe-123')
        portfolio = Portfolio.objects.create(profile=profile, slug='john-doe-123', professional_summary='', skills=[], work_experience=[], education=[], template_choice='default')
        self.assertEqual(portfolio.slug, 'john-doe-123')
