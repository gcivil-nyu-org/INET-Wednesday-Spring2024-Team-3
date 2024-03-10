from django.urls import path
from . import views

urlpatterns = [
    path("", views.forum_home, name="forum_home"),
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/add_comment/', views.add_comment, name='add_comment'),
]
