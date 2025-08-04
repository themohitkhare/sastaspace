from django.urls import path
from .views import PortfolioMeView, PortfolioPublicView

urlpatterns = [
    path('portfolio/me/', PortfolioMeView.as_view(), name='portfolio-me'),
    path('portfolio/public/<slug:slug>/', PortfolioPublicView.as_view(), name='portfolio-public'),
]
