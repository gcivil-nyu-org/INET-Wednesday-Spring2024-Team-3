from django.urls import path
from . import views

urlpatterns = [
    path("", views.forum_home_view, name="forum_home_view"),
]
