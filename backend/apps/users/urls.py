from django.urls import path
from .views import UserListView, login_view, register_view, logout_view, get_current_user

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('accounts/login/', login_view, name='api-login'),
    path('accounts/signup/', register_view, name='api-register'),
    path('accounts/logout/', logout_view, name='api-logout'),
    path('users/me/', get_current_user, name='get-current-user'),
]
