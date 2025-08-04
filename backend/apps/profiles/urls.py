from django.urls import path
from .views import OnboardView

urlpatterns = [
    path('profiles/onboard/', OnboardView.as_view(), name='profile-onboard'),
]
