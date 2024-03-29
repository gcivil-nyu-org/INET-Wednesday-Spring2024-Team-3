"""
URL configuration for taxiapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("", views.home_view, name="home"),
    path("confirm/", views.confirm_view, name="confirm"),
    path("reset/", views.reset_view, name="reset"),
    path("success/", views.success_view, name="success"),
    path("profile/", views.profile_view, name="profile"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.save_profile_view, name="save_profile"),
    path("faq/", views.faq, name="faq"),
    path("forum/", include("forum.urls")),
    path("rideshare/", include("rideshare.urls")),

]
