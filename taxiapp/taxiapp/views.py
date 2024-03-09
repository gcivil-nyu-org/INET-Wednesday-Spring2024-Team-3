from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import FormView
from django import forms
import boto3
from django.conf import settings
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import logging
import re

logger = logging.getLogger(__name__)

class LoginForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class CustomLoginView(LoginView):
    template_name = 'login.html'
    form_class = LoginForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(request=self.request, username=username, password=password)
        if user is not None:
            login(self.request, user, backend='taxiapp.cognito_backend.CognitoBackend')
            logger.debug(f"User {username} logged in: {self.request.user.is_authenticated}")
            return redirect("/")
        else:
            try:
                logger.error(f"Authentication failed for user {username}")
                client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
                secret_hash = get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
                response = client.admin_initiate_auth(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    AuthFlow="ADMIN_NO_SRP_AUTH",
                    AuthParameters={
                        "USERNAME": username,
                        "PASSWORD": password,
                        "SECRET_HASH": secret_hash,
                    },
                )
                id_token = response["AuthenticationResult"]["IdToken"]
                access_token = response["AuthenticationResult"]["AccessToken"]

                self.request.session["id_token"] = id_token
                self.request.session["access_token"] = access_token

                django_user, created = User.objects.get_or_create(username=username)
                login(self.request, django_user, backend='taxiapp.cognito_backend.CognitoBackend')
                
                return redirect("/")

            except client.exceptions.UserNotConfirmedException:
                messages.error(self.request, "User account is not confirmed. Please check your email for the confirmation code.")
                return redirect("confirm")
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "NotAuthorizedException":
                    messages.error(self.request, "Invalid username or password.")
                elif error_code == "UserNotFoundException":
                    messages.error(self.request, "User does not exist.")
                else:
                    messages.error(self.request, f"An error occurred: {error_code}.")
                return self.form_invalid(form)
class CustomLogoutView(LogoutView):
    next_page = '/'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            return self.get(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.next_page)

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    full_name = forms.CharField(max_length=255)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        full_name = cleaned_data.get("full_name", "").split()
        if len(full_name) < 2:
            raise forms.ValidationError("Please enter your full name (both given and family name).")

        if len(password) < 8 or not any(char.isdigit() for char in password) or not any(char.isupper() for char in password) or not any(char.islower() for char in password) or not any(char in "!@#$%^&*()_+" for char in password):
            raise forms.ValidationError("Password does not meet the requirements.")
        return cleaned_data

class RegisterView(FormView):
    template_name = 'register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('confirm')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        full_name = form.cleaned_data['full_name'].split()

        given_name = full_name[0]
        family_name = " ".join(full_name[1:])

        secret_hash = get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)
        client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)

        try:
            client.sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=secret_hash,
                Username=username,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "given_name", "Value": given_name},
                    {"Name": "family_name", "Value": family_name},
                ],
            )
            messages.success(
                self.request,
                "Registration successful. Please check your email to confirm your account.",
            )
            return super().form_valid(form)
        except ClientError as e:
            if e.response["Error"]["Code"] == "UsernameExistsException":
                form.add_error('username', "A user with this username already exists.")
            else:
                messages.error(
                    self.request, "An error occurred: " + e.response["Error"]["Message"]
                )
            return self.form_invalid(form)

class ConfirmForm(forms.Form):
    username = forms.CharField(max_length=150)
    confirmation_code = forms.CharField(max_length=6)

class ConfirmView(FormView):
    template_name = 'confirm.html'
    form_class = ConfirmForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        confirmation_code = form.cleaned_data['confirmation_code']
        
        try:
            client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
            secret_hash = get_secret_hash(
                username,
                settings.COGNITO_APP_CLIENT_ID,
                settings.COGNITO_APP_CLIENT_SECRET,
            )
            response = client.confirm_sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=secret_hash,
                Username=username,
                ConfirmationCode=confirmation_code,
            )
            messages.success(self.request, "Your account has been confirmed. Please log in.")
            return super().form_valid(form)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "CodeMismatchException":
                form.add_error('confirmation_code', "Invalid confirmation code. Please try again.")
            elif error_code == "ExpiredCodeException":
                form.add_error('confirmation_code', "Confirmation code expired. Please request a new code.")
            else:
                messages.error(self.request, "Failed to confirm account. Please try again later.")
                logger.error(f"Failed to confirm account for username {username}: {e}")
            return self.form_invalid(form)

class CustomPasswordResetView(PasswordResetView):
    template_name = 'reset.html'
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'password_reset_email.html'
    
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
            client.forgot_password(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=email,
                SecretHash=get_secret_hash(
                    email,
                    settings.COGNITO_APP_CLIENT_ID,
                    settings.COGNITO_APP_CLIENT_SECRET,
                ),
            )
            logger.debug(f"Password reset requested for email {email}")
            return super().form_valid(form)
        except ClientError as e:
            logger.error(f"Error initiating password reset for {email}: {e}")
            form.add_error(None, "Failed to initiate password reset. Please try again later.")
            return self.form_invalid(form)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        new_password = form.cleaned_data["new_password1"]
        uid = self.kwargs.get("uidb64")
        token = self.kwargs.get("token")
        
        try:
            username = force_str(urlsafe_base64_decode(uid))
            client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
            client.confirm_forgot_password(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash=get_secret_hash(
                    username,
                    settings.COGNITO_APP_CLIENT_ID,
                    settings.COGNITO_APP_CLIENT_SECRET,
                ),
                Username=username,
                ConfirmationCode=token,
                Password=new_password,
            )
            logger.debug(f"Password reset for username {username}")
            return super().form_valid(form)
        except ClientError as e:
            logger.error(f"Failed to reset password for username {username}: {e}")
            if e.response["Error"]["Code"] == "CodeMismatchException":
                form.add_error(None, "Invalid verification code. Please try again.")
            else:
                form.add_error(None, "Failed to reset password. Please try again later.")
            return self.form_invalid(form)

def home_view(request):
    return render(request, 'home.html')

def success_view(request):
    return render(request, 'home.html')

@login_required
def profile_view(request):
    if not request.user.is_authenticated:
        return redirect("/")
    client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
    cognito_username = request.user.username

    try:
        response = client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID, Username=cognito_username
        )
        user_attributes = {
            attr["Name"]: attr["Value"] for attr in response["UserAttributes"]
        }
        context = {
            "first_name": user_attributes.get("given_name", ""),
            "middle_name": user_attributes.get("middle_name", ""),
            "last_name": user_attributes.get("family_name", ""),
            "username": cognito_username,
            "email": user_attributes.get("email", ""),
            "phone_number": user_attributes.get("phone_number", ""),
            "address": user_attributes.get("address", ""),
        }
    except Exception as e:
        messages.error(request, f"Failed to retrieve profile information: {str(e)}")
        context = {}

    return render(request, "profile.html", context)

@login_required  
def save_profile_view(request):
    if request.method == 'POST':
        client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
        cognito_username = request.user.username
        
        updated_attributes = [
            {'Name': 'given_name', 'Value': request.POST.get('first_name')},
            {'Name': 'middle_name', 'Value': request.POST.get('middle_name')},
            {'Name': 'family_name', 'Value': request.POST.get('last_name')},
            {'Name': 'email', 'Value': request.POST.get('email')},
            {'Name': 'phone_number', 'Value': request.POST.get('phone_number')},
            {'Name': 'address', 'Value': request.POST.get('address')},
        ]
        
        try:
            client.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=cognito_username,
                UserAttributes=updated_attributes
            )
            messages.success(request, 'Profile updated successfully.')
        except Exception as e:
            messages.error(request, f'Failed to update profile: {str(e)}')
        
        return redirect('/profile')
    else:
        return redirect('/profile')

def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('UTF-8'), 
                   msg=message.encode('UTF-8'),
                   digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()