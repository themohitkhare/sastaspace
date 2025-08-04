from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer
from .ai_service import generate_portfolio_from_data
from apps.portfolio.models import Portfolio
from apps.portfolio.serializers import PortfolioSerializer
from django.core.files.storage import default_storage
import os

class OnboardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resume_file = request.FILES.get('resume_file')
        linkedin_url = request.data.get('linkedin_url')
        if not resume_file or not linkedin_url:
            return Response({'error': 'Resume and LinkedIn URL required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Save resume file
        file_path = default_storage.save(f'resumes/{resume_file.name}', resume_file)
        resume_text = ""  # TODO: Extract text from file
        linkedin_username = linkedin_url.rstrip('/').split('/')[-1]
        profile = Profile.objects.create(
            user=request.user,
            linkedin_url=linkedin_url,
            linkedin_username=linkedin_username,
            resume_file=file_path,
            resume_text=resume_text
        )
        ai_result = generate_portfolio_from_data(resume_text, "")
        profile.ai_analysis_cache = ai_result
        profile.save()
        # Parse AI result and create Portfolio
        # TODO: Parse JSON from ai_result
        portfolio = Portfolio.objects.create(
            profile=profile,
            slug=linkedin_username,
            professional_summary="",
            skills=[],
            work_experience=[],
            education=[],
            template_choice='default'
        )
        return Response(PortfolioSerializer(portfolio).data, status=status.HTTP_201_CREATED)
