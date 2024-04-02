from django.urls import path
from . import views

urlpatterns = [
    path("", views.forum_home, name="forum_home"),
    path("post/create/", views.post_create, name="post_create"),
    path("<int:post_id>/", views.post_detail, name="post_detail"),
    path("<int:post_id>/add_comment/", views.add_comment, name="add_comment"),
    path("api/posts", views.posts_api, name='posts_api'),
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    path('<int:post_id>/upvote/', views.upvote_post, name='upvote_post'),
    path('<int:post_id>/downvote/', views.downvote_post, name='downvote_post'),
]
