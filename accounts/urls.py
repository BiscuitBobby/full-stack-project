# accounts/urls.py
from django.urls import path
from . import views # Keep the old views
from .views import RegisterAPIView, LoginAPIView, LogoutAPIView, UserProfileAPIView # Import new API views

urlpatterns = [
    # API Auth URLs
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('profile/', UserProfileAPIView.as_view(), name='profile'),
]