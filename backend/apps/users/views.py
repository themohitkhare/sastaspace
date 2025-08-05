from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import CustomUser
from .serializers import CustomUserSerializer

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = CustomUser.objects.get(email=email)
        if user.check_password(password):
            login(request, user)
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    email = request.data.get('email')
    password1 = request.data.get('password1')
    password2 = request.data.get('password2')
    
    if not email or not password1 or not password2:
        return Response({'error': 'Email, password1, and password2 are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if password1 != password2:
        return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)
    
    if CustomUser.objects.filter(email=email).exists():
        return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password1
        )
        login(request, user)
        return Response({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username
            }
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username
    }, status=status.HTTP_200_OK)
