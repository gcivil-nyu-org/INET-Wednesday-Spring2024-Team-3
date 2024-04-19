from django.urls import path
from user.views import public_user_profile, send_friend_request, accept_friend_request, unfriend, friend_requests
from user.views import reject_friend_request, cancel_friend_request, search_people

urlpatterns = [
    path('<str:username>/', public_user_profile, name='public_user'),
    path('send_friend_request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('accept_friend_request/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('reject_friend_request/<int:request_id>/', reject_friend_request, name='reject_friend_request'),
    path('unfriend/<int:user_id>/', unfriend, name='unfriend'),
    path('friend_requests/', friend_requests, name='friend_requests'),
    path('cancel_friend_request/<int:user_id>/', cancel_friend_request, name='cancel_friend_request'),
    path('search', search_people, name='search_people')

]