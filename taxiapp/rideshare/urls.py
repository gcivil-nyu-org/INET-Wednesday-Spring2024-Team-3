from django.urls import path
from . import views

urlpatterns = [
    path("", views.rideshare_home_view, name="rideshare_home_view"),
    path(
        "api/google-maps-api-key/",
        views.google_maps_api_key,
        name="google_maps_api_key",
    ),
    path("api/compare-fares/", views.compare_fares, name="compare_fares"),
    path("api/uber-fare/", views.get_uber_fare, name="uber_fare"),
    path("api/taxi-fare/", views.get_taxi_fare, name="taxi_fare"),
]
