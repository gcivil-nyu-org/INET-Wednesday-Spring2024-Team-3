from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import boto3
from django.conf import settings
from django.contrib import messages
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import logging
import re
import os

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user, backend="taxiapp.cognito_backend.CognitoBackend")
            return redirect("/")
        else:
            try:
                client = boto3.client(
                    "cognito-idp", region_name=settings.COGNITO_AWS_REGION
                )
                secret_hash = get_secret_hash(
                    username,
                    settings.COGNITO_APP_CLIENT_ID,
                    settings.COGNITO_APP_CLIENT_SECRET,
                )
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

                # Store tokens in session, cookies, or send to client
                #  May change in the future
                request.session["id_token"] = id_token
                request.session["access_token"] = access_token

                # Create or update Django user and log in
                django_user, created = User.objects.get_or_create(username=username)
                login(
                    request,
                    django_user,
                    backend="taxiapp.cognito_backend.CognitoBackend",
                )
                return redirect("/")

            except client.exceptions.UserNotConfirmedException:
                messages.error(
                    request,
                    "User account is not confirmed. Please check your email for the confirmation code.",
                )
                return redirect("confirm")
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "NotAuthorizedException":
                    messages.error(request, "Invalid username or password.")
                elif error_code == "UserNotFoundException":
                    messages.error(request, "User does not exist.")
                else:
                    messages.error(request, f"An error occurred: {error_code}.")
                return render(request, "login.html", {"error": "Invalid credentials"})

    return render(request, "login.html")


# Registration view
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        full_name = request.POST.get("full_name", "").split()

        # Basic validation for full_name
        if len(full_name) < 2:
            messages.error(
                request, "Please enter your full name (both given and family name)."
            )
            return render(request, "register.html")

        given_name = full_name[0]
        family_name = " ".join(full_name[1:])
        # Check password confirmation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html")

        # Password validation
        if (
            len(password) < 8
            or not any(char.isdigit() for char in password)
            or not any(char.isupper() for char in password)
            or not any(char.islower() for char in password)
            or not any(char in "!@#$%^&*()_+" for char in password)
        ):
            messages.error(request, "Password does not meet the requirements.")
            return render(request, "register.html")

        secret_hash = get_secret_hash(
            username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET
        )
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
                request,
                "Registration successful. Please check your email to confirm your account.",
            )
            return redirect("confirm")
        except ClientError as e:
            if e.response["Error"]["Code"] == "UsernameExistsException":
                messages.error(request, "A user with this username already exists.")
            else:
                messages.error(
                    request, "An error occurred: " + e.response["Error"]["Message"]
                )
            return render(request, "register.html")

    return render(request, "register.html")


def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(
        client_secret.encode("UTF-8"),
        msg=message.encode("UTF-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()


def home_view(request):
    google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    context = {
        'google_maps_api_key': google_maps_api_key
    }
    return render(request, 'home.html', context)


def reset_view(request):
    step = "request"  # Default step

    if request.method == "POST":
        if "request_reset" in request.POST:  # Handling the initial reset request
            user_identifier = request.POST.get("user_identifier", "").strip()

            if not user_identifier:
                messages.error(request, "Please enter a valid email or username.")
            elif "@" in user_identifier and not re.match(
                r"[^@]+@[^@]+\.[^@]+", user_identifier
            ):
                messages.error(request, "Please enter a valid email address.")
            else:
                try:
                    client = boto3.client(
                        "cognito-idp", region_name=settings.COGNITO_AWS_REGION
                    )
                    client.forgot_password(
                        ClientId=settings.COGNITO_APP_CLIENT_ID,
                        Username=user_identifier,
                        SecretHash=get_secret_hash(
                            user_identifier,
                            settings.COGNITO_APP_CLIENT_ID,
                            settings.COGNITO_APP_CLIENT_SECRET,
                        ),
                    )
                    messages.success(
                        request, "Password reset code sent. Please check your email."
                    )
                    step = "confirm"  # Move to confirmation step
                except ClientError as e:
                    logger.error(
                        f"Error initiating password reset for {user_identifier}: {e}"
                    )
                    messages.error(
                        request,
                        "Failed to initiate password reset. Please try again later.",
                    )

        elif "confirm_reset" in request.POST:  # Handling the confirmation step
            username = request.POST.get("username", "").strip()
            verification_code = request.POST.get("verification_code", "").strip()
            new_password = request.POST.get("new_password", "").strip()

            if not username or not verification_code or not new_password:
                messages.error(request, "All fields are required.")
            else:
                try:
                    client = boto3.client(
                        "cognito-idp", region_name=settings.COGNITO_AWS_REGION
                    )
                    client.confirm_forgot_password(
                        ClientId=settings.COGNITO_APP_CLIENT_ID,
                        SecretHash=get_secret_hash(
                            username,
                            settings.COGNITO_APP_CLIENT_ID,
                            settings.COGNITO_APP_CLIENT_SECRET,
                        ),
                        Username=username,
                        ConfirmationCode=verification_code,
                        Password=new_password,
                    )
                    messages.success(
                        request,
                        "Your password has been reset successfully. Please log in with your new password.",
                    )
                    return redirect("login")
                except ClientError as e:
                    logger.error(
                        f"Failed to reset password for username {username}: {e}"
                    )
                    if e.response["Error"]["Code"] == "CodeMismatchException":
                        messages.error(
                            request, "Invalid verification code. Please try again."
                        )
                    else:
                        messages.error(
                            request, "Failed to reset password. Please try again later."
                        )

    return render(
        request,
        "reset.html",
        {"step": step, "username": user_identifier if step == "confirm" else ""},
    )


def success_view(request):
    return render(request, "home.html")


def confirm_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        confirmation_code = request.POST.get("confirmation_code", "").strip()

        # Basic input validation
        if not username or not confirmation_code:
            messages.error(request, "Username and confirmation code are required.")
            return render(request, "confirm.html")

        try:
            client = boto3.client(
                "cognito-idp", region_name=settings.COGNITO_AWS_REGION
            )
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
            messages.success(request, "Your account has been confirmed. Please log in.")
            return redirect("login")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "CodeMismatchException":
                error_message = "Invalid confirmation code. Please try again."
            elif error_code == "ExpiredCodeException":
                error_message = "Confirmation code expired. Please request a new code."
            else:
                error_message = "Failed to confirm account. Please try again later."

            logger.error(f"Failed to confirm account for username {username}: {e}")
            messages.error(request, error_message)
            return render(request, "confirm.html")
    else:
        return render(request, "confirm.html")


# def profile_view(request):
#     if not request.user.is_authenticated:
#         return redirect('/')
#     return render(request, 'profile.html')


def logout_view(request):
    logout(request)
    return redirect("/")


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
    if request.method == "POST":
        client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
        cognito_username = request.user.username

        updated_attributes = [
            {"Name": "given_name", "Value": request.POST.get("first_name")},
            {"Name": "middle_name", "Value": request.POST.get("middle_name")},
            {"Name": "family_name", "Value": request.POST.get("last_name")},
            {"Name": "email", "Value": request.POST.get("email")},
            {"Name": "phone_number", "Value": request.POST.get("phone_number")},
            {"Name": "address", "Value": request.POST.get("address")},
        ]

        try:
            client.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=cognito_username,
                UserAttributes=updated_attributes,
            )
            messages.success(request, "Profile updated successfully.")
        except Exception as e:
            messages.error(request, f"Failed to update profile: {str(e)}")

        return redirect("/profile")
    else:
        return redirect("/profile")
