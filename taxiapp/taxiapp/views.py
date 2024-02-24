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
            return redirect('success')
        else:

            try:
                client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
                secret_hash = get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
                client.admin_initiate_auth(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    AuthFlow='ADMIN_NO_SRP_AUTH',
                    AuthParameters={
                        'USERNAME': username,
                        'PASSWORD': password,
                        'SECRET_HASH': secret_hash
                    }
                )
            except client.exceptions.UserNotConfirmedException:
                # Resend confirmation code
                client.resend_confirmation_code(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    Username=username,
                    SecretHash=secret_hash
                )
                messages.error(request, "User account is not confirmed. Please check your email for the confirmation code.")
                return redirect('confirm')  # Redirect to a page where users can enter their confirmation code
            except ClientError as e:
                # Handle other Cognito exceptions
                error_code = e.response['Error']['Code']
                if error_code == 'NotAuthorizedException':
                    messages.error(request, "Invalid username or password.")
                elif error_code == 'UserNotFoundException':
                    messages.error(request, "User does not exist.")
                else:
                    messages.error(request, f"An error occurred: {error_code}.")
                return render(request, 'login.html')

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
            return redirect('confirm')
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                messages.error(request, "A user with this username already exists.")
            else:
                messages.error(request, "An error occurred: " + e.response['Error']['Message'])
            return render(request, 'register.html')

    return render(request, 'register.html')

def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('UTF-8'), 
                   msg=message.encode('UTF-8'), 
                   digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def home_view(request):
    return render(request, 'home.html')

def reset_view(request):
    if request.method == 'POST' and 'request_reset' in request.POST:
        username = request.POST.get('username')

        client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
        try:
            response = client.forgot_password(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=username,
                # If you're using client secrets
                SecretHash=get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
            )
            messages.success(request, "Password reset code sent. Please check your email.")
            return render(request, 'reset_confirm.html', {'username': username})  # Render a template to enter the verification code and new password
        except ClientError as e:
            messages.error(request, f"Failed to initiate password reset: {e.response['Error']['Code']}")
            return render(request, 'reset.html')

    return render(request, 'reset.html')

def reset_confirm_view(request):
    if request.method == 'POST' and 'confirm_reset' in request.POST:
        username = request.POST.get('username')
        verification_code = request.POST.get('verification_code')
        new_password = request.POST.get('new_password')

        client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
        try:
            response = client.confirm_forgot_password(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET),
                Username=username,
                ConfirmationCode=verification_code,
                Password=new_password
            )
            messages.success(request, "Your password has been reset successfully. Please log in with your new password.")
            return redirect('login')
        except ClientError as e:
            messages.error(request, f"Failed to reset password: {e.response['Error']['Code']}")
            return render(request, 'reset_confirm.html', {'username': username})

    return render(request, 'reset_confirm.html')



def success_view(request):
    return render(request, 'success.html')

def confirm_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        confirmation_code = request.POST.get('confirmation_code')
        try:
            client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
            secret_hash = get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
            response = client.confirm_sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=secret_hash,
                Username=username,
                ConfirmationCode=confirmation_code
            )
            messages.success(request, "Your account has been confirmed. Please log in.")
            return redirect('login')
        except ClientError as e:
            messages.error(request, f"Failed to confirm account: {e.response['Error']['Code']}")
            return render(request, 'confirm.html')
    else:
        return render(request, 'confirm.html')
    
    
def profile_view(request):
    return render(request, 'profile.html')
    

