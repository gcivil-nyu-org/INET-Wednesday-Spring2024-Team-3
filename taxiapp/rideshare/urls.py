from django.urls import path
from . import views

urlpatterns = [
    path("", views.rideshare_home_view, name="rideshare_home_view"),
]
