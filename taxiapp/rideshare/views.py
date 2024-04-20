import json
import logging
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import joblib
import geopy.distance

logger = logging.getLogger(__name__)


def rideshare_home_view(request):
    return HttpResponse("Hello, this is the rideshare home view!")


def google_maps_api_key(request):
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    return JsonResponse({"api_key": google_maps_api_key})


@csrf_exempt
def compare_fares(request):
    if request.method == "POST":
        data = json.loads(request.body)

        startlat = data.get("startlat")
        startlng = data.get("startlng")
        startCoord = [startlat, startlng]
        endlat = data.get("endlat")
        endlng = data.get("endlng")
        endCoord = [endlat, endlng]
        passengers = data.get("num_passengers")
        if passengers <= 4:
            passengers = 1
        elif passengers <= 6:
            passengers = 6
        else:
            passengers = passengers
        dis = geopy.distance.geodesic(startCoord, endCoord).km

        # Call the ML models to retrieve estimated Uber and Taxi fares
        uber_fare = get_uber_fare(dis, passengers)
        taxi_fare = get_taxi_fare(dis, passengers)

        # Prepare the response data
        fare_data = {
            "uber_fare": round(uber_fare * 2, 2),
            "taxi_fare": round(taxi_fare * 2, 2),
        }

        return JsonResponse(fare_data)

    return JsonResponse({"error": "Invalid request method"})


def get_uber_fare(dis, passengers):
    uber_model = joblib.load("rideshare/models/Uber_Linear_Regression.joblib")

    params = {"distance": dis, "passenger_count": passengers}

    input_features = [[params["distance"], params["passenger_count"]]]
    estFare = uber_model.predict(input_features)
    return estFare[0]


def get_taxi_fare(dis, passengers):
    taxi_model = joblib.load("rideshare/models/Taxi_Linear_Regression.joblib")

    params = {"distance": dis, "passenger_count": passengers}

    input_features = [[params["distance"], params["passenger_count"]]]
    estFare = taxi_model.predict(input_features)
    return estFare[0]
