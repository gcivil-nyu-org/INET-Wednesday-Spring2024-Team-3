from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
import boto3
from django.conf import settings
from django.contrib import messages
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64

# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to a success page.
            return redirect('home') 
        else:
            # Return an error message
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

# Registration view
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        full_name = request.POST.get('full_name', '').split()

        # Basic validation for full_name
        if len(full_name) < 2:
            messages.error(request, "Please enter your full name (both given and family name).")
            return render(request, 'register.html')

        given_name = full_name[0]
        family_name = ' '.join(full_name[1:])
        # Check password confirmation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        # Password validation
        if len(password) < 8 or not any(char.isdigit() for char in password) or not any(char.isupper() for char in password) or not any(char.islower() for char in password) or not any(char in '!@#$%^&*()_+' for char in password):
            messages.error(request, "Password does not meet the requirements.")
            return render(request, 'register.html')
        
        secret_hash = get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
        client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)

        try:
            client.sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=secret_hash,
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'given_name', 'Value': given_name},
                    {'Name': 'family_name', 'Value': family_name},
                ]
            )
            messages.success(request, "Registration successful. Please check your email to confirm your account.")
            return redirect('login')
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                messages.error(request, "A user with this username already exists.")
            else:
                messages.error(request, "An error occurred: " + e.response['Error']['Message'])
            return render(request, 'register.html')

    return render(request, 'register.html')

def home_view(request):
    return render(request, 'home.html')

def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('UTF-8'), 
                   msg=message.encode('UTF-8'), 
                   digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()
