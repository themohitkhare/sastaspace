from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.profiles.urls')),
    path('api/', include('apps.portfolio.urls')),
    path('api/', include('apps.users.urls')),
    path('accounts/', include('allauth.urls')),
]
