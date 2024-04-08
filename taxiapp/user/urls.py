from django.urls import path
from .views import *

urlpatterns = [
    path('<str:username>/', public_user_profile, name='public_user'),
    path('send_friend_request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('accept_friend_request/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('unfriend/<int:user_id>/', unfriend, name='unfriend'),
    path('friend_requests/', friend_requests, name='friend_requests'),
]