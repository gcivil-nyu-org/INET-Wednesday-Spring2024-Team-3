from django.urls import path
from . import views

urlpatterns = [
    path('', views.tools_home, name='tools_home'),
]