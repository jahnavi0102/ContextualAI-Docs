from django.urls import path
from .views import register_user, get_current_user

urlpatterns = [
    path('register/', register_user, name='register_user'),
    path('me/', get_current_user, name='user-detail'),
]