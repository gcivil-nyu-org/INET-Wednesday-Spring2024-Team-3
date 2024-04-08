from django.urls import path
from .views import public_user_profile

urlpatterns = [
    path('<str:username>/', public_user_profile, name='public_user'),
]