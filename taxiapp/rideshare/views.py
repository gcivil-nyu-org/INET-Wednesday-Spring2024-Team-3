import json
import logging
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)

def rideshare_home_view(request):
    return HttpResponse("Hello, this is the rideshare home view!")

def google_maps_api_key(request):
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
    return JsonResponse({'api_key': google_maps_api_key})

@csrf_exempt
def compare_fares(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        start_address = data.get('start_address')
        end_address = data.get('end_address')
        
        # Call the endpoints to acquire fare data from Uber and Lyft APIs
        uber_fare = get_uber_fare(start_address, end_address)
        lyft_fare = get_lyft_fare(start_address, end_address)
        
        # Prepare the response data
        fare_data = {
            'uber_fare': uber_fare,
            'lyft_fare': lyft_fare,
        }
        
        return JsonResponse(fare_data)
    
    return JsonResponse({'error': 'Invalid request method'})

def get_uber_fare(start_address, end_address):
    uber_api_url = 'https://api.uber.com/v1.2/estimates/price'
    client_id = settings.UBER_CLIENT_ID
    client_secret = settings.UBER_CLIENT_SECRET
    token_url = 'https://login.uber.com/oauth/v2/token'
    token_params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'request',
    }

    token_response = requests.post(token_url, data=token_params)
    logger.debug("test")

    if token_response.status_code == 200:
        access_token = token_response.json()['access_token']
        params = {
            'start_latitude': start_address['lat'],
            'start_longitude': start_address['lng'],
            'end_latitude': end_address['lat'],
            'end_longitude': end_address['lng'],
        }
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        response = requests.get(uber_api_url, params=params, headers=headers)
        logger.debug(response)

        if response.status_code == 200:
            fare_data = response.json()
            if 'prices' in fare_data and len(fare_data['prices']) > 0:
                fare = fare_data['prices'][0]['estimate']
                return int(fare.split('-')[0].strip('$'))
            else:
                return {'error': 'No fare estimate available'}
        else:
            return {'error': 'Failed to retrieve Uber fare'}
    else:
        return {'error': 'Failed to obtain access token'}

def get_lyft_fare(start_address, end_address):
    return 0
    lyft_api_key = settings.LYFT_API_KEY
    lyft_api_url = 'https://api.lyft.com/v1/cost'
    params = {
        'start_lat': start_address['lat'],
        'start_lng': start_address['lng'],
        'end_lat': end_address['lat'],
        'end_lng': end_address['lng'],
    }
    headers = {
        'Authorization': f'Bearer {lyft_api_key}',
    }
    response = requests.get(lyft_api_url, params=params, headers=headers)
    
    if response.status_code == 200:
        fare_data = response.json()
        # Extract the relevant fare information from the API response
        # and return it
        return fare_data
    else:
        return {'error': 'Failed to retrieve Lyft fare'}