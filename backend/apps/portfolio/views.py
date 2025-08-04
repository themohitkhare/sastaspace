from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from .models import Portfolio
from .serializers import PortfolioSerializer
from apps.profiles.models import Profile

class PortfolioMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        portfolio = Portfolio.objects.get(profile=profile)
        return Response(PortfolioSerializer(portfolio).data)

    def put(self, request):
        profile = Profile.objects.get(user=request.user)
        portfolio = Portfolio.objects.get(profile=profile)
        serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PortfolioPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            portfolio = Portfolio.objects.get(slug=slug)
            return Response(PortfolioSerializer(portfolio).data)
        except Portfolio.DoesNotExist:
            return Response({'error': 'Portfolio not found.'}, status=status.HTTP_404_NOT_FOUND)
