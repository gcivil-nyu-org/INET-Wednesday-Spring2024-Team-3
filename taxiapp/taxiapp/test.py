from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from user.models import FriendRequest, Friendship
from forum.models import Post, Comment
from taxiapp.views import get_secret_hash
from unittest.mock import patch, MagicMock, ANY
from taxiapp.cognito_backend import CognitoBackend
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import hashlib
import hmac
import base64
from botocore.exceptions import ClientError
import os


class ViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        Post.objects.create(title="Post 1", content="Content 1", user=self.user)
        Post.objects.create(title="Post 2", content="Content 2", user=self.user)
        Post.objects.create(title="Post 3", content="Content 3", user=self.user)

    def test_login_view_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_login_view_post_success(self):
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "12345"}
        )
        self.assertRedirects(response, "/")

    def test_login_view_post_failure(self):
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Invalid credentials" in response.context["error"])

    def tearDown(self):
        self.user.delete()

    @patch("taxiapp.views.hmac.new")
    def test_get_secret_hash(self, mock_new):
        username = "test_user"
        client_id = "client_id"
        client_secret = "client_secret"
        expected_result = b"expected_result"

        mock_hmac_instance = mock_new.return_value
        mock_hmac_instance.digest.return_value = expected_result

        result = get_secret_hash(username, client_id, client_secret)

        mock_new.assert_called_once_with(
            client_secret.encode("UTF-8"),
            msg=(username + client_id).encode("UTF-8"),
            digestmod=mock.ANY,
        )

        self.assertEqual(result, base64.b64encode(expected_result).decode())

    def test_home_view(self):
        os.environ["GOOGLE_MAPS_API_KEY"] = "FAKE_API_KEY"

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["google_maps_api_key"], "FAKE_API_KEY")

        latest_posts = response.context["latest_posts"]
        self.assertEqual(len(latest_posts), 3)

    def test_faq_page(self):
        response = self.client.get(reverse("faq"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "faq.html")
        self.assertIn("faq_data", response.context)

        expected_question = "How do I sign up for an account?"
        found = any(
            item["question"] == expected_question
            for item in response.context["faq_data"]
        )
        self.assertTrue(found, "Expected question not found in FAQ data")

    def test_success_view(self):
        response = self.client.get(reverse("success"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "home.html")

    @patch("taxiapp.views.logout")
    def test_logout_view(self, mock_logout):
        response = self.client.post(reverse("logout"))
        mock_logout.assert_called_once_with(ANY)
        self.assertRedirects(response, "/", status_code=302)


class RegisterViewTests(TestCase):

    def setUp(self):
        self.url = reverse("register")

    def test_register_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "register.html")

    @patch("boto3.client")
    def test_register_view_post_success(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.return_value = {
            "UserConfirmed": True,
        }

        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "full_name": "New User",
            },
        )

        self.assertRedirects(response, reverse("confirm"))

    @patch("boto3.client")
    def test_register_view_valid_registration(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.return_value = {"UserConfirmed": True}
        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "full_name": "New User",
            },
        )
        self.assertRedirects(response, reverse("confirm"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0]),
            "Registration successful. Please check your email to confirm your account.",
        )

    @patch("boto3.client")
    def test_register_view_password_confirmation_failure(self, mock_boto3_client):
        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Password123!",
                "confirm_password": "WrongPassword123!",
                "full_name": "New User",
            },
        )
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Passwords do not match.", str(messages[0]))

    @patch("boto3.client")
    def test_register_view_invalid_password_requirements(self, mock_boto3_client):
        response = self.client.post(
            self.url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "pass",  # Invalid password
                "confirm_password": "pass",
                "full_name": "New User",
            },
        )
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Password does not meet the requirements.", str(messages[0]))

    @patch("boto3.client")
    def test_register_view_username_already_exists(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.side_effect = ClientError(
            {
                "Error": {
                    "Code": "UsernameExistsException",
                    "Message": "Username already exists",
                }
            },
            operation_name="SignUp",
        )
        response = self.client.post(
            self.url,
            {
                "username": "existinguser",
                "email": "existinguser@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "full_name": "Existing User",
            },
        )
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("A user with this username already exists.", str(messages[0]))


class ResetViewTests(TestCase):

    def setUp(self):
        self.url = reverse("reset")

    def test_empty_user_identifier(self):
        response = self.client.post(
            self.url, {"request_reset": True, "user_identifier": ""}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Please enter a valid email or username.", [str(m) for m in messages]
        )
        self.assertTemplateUsed(response, "reset.html")

    def test_invalid_email_format(self):
        response = self.client.post(
            self.url, {"request_reset": True, "user_identifier": "invalidemail@"}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("Please enter a valid email address.", [str(m) for m in messages])
        self.assertTemplateUsed(response, "reset.html")

    @patch("boto3.client")
    def test_successful_reset_request(self, mock_boto3_client):
        mock_boto3_client.return_value.forgot_password.return_value = {}
        response = self.client.post(
            self.url, {"request_reset": True, "user_identifier": "user@example.com"}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Password reset code sent. Please check your email.",
            [str(m) for m in messages],
        )
        self.assertTemplateUsed(response, "reset.html")

    @patch("boto3.client")
    def test_cognito_failure_on_reset_request(self, mock_boto3_client):
        mock_boto3_client.return_value.forgot_password.side_effect = ClientError(
            {"Error": {"Code": "NetworkError", "Message": "Network error"}},
            operation_name="forgot_password",
        )
        response = self.client.post(
            self.url, {"request_reset": True, "user_identifier": "user@example.com"}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Failed to initiate password reset. Please try again later.",
            [str(m) for m in messages],
        )
        self.assertTemplateUsed(response, "reset.html")

    def test_empty_fields_on_confirmation_step(self):
        response = self.client.post(
            self.url,
            {
                "confirm_reset": True,
                "username": "",
                "verification_code": "",
                "new_password": "",
            },
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn("All fields are required.", [str(m) for m in messages])
        self.assertTemplateUsed(response, "reset.html")

    @patch("boto3.client")
    def test_invalid_verification_code(self, mock_boto3_client):
        error_response = {
            "Error": {
                "Code": "CodeMismatchException",
                "Message": "Invalid verification code",
            }
        }
        mock_boto3_client.return_value.confirm_forgot_password.side_effect = (
            ClientError(error_response, "confirm_forgot_password")
        )

        response = self.client.post(
            reverse("reset"),
            {
                "confirm_reset": True,
                "username": "testuser",
                "verification_code": "wrong-code",
                "new_password": "NewPassword123!",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Invalid verification code. Please try again.", [str(m) for m in messages]
        )

        self.assertTemplateUsed(response, "reset.html")
        self.assertEqual(response.status_code, 200)

    @patch("boto3.client")
    def test_successful_password_reset(self, mock_boto3_client):
        mock_boto3_client.return_value.confirm_forgot_password.return_value = {}
        response = self.client.post(
            self.url,
            {
                "confirm_reset": True,
                "username": "user",
                "verification_code": "correctcode",
                "new_password": "NewPass123!",
            },
        )
        self.assertRedirects(response, reverse("login"))

    @patch("boto3.client")
    def test_password_reset_failure_general(self, mock_boto3_client):
        error_response = {"Error": {"Code": "NetworkError", "Message": "Network error"}}
        mock_boto3_client.return_value.confirm_forgot_password.side_effect = (
            ClientError(error_response, "confirm_forgot_password")
        )

        response = self.client.post(
            self.url,
            {
                "confirm_reset": True,
                "username": "testuser",
                "verification_code": "123456",
                "new_password": "NewPass123!",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Failed to reset password. Please try again later.",
            [str(m) for m in messages],
        )

        self.assertTemplateUsed(response, "reset.html")
        self.assertEqual(response.status_code, 200)


class ConfirmViewTests(TestCase):
    def setUp(self):
        self.url = reverse("confirm")

    @patch("boto3.client")
    def test_post_with_empty_fields(self, mock_boto3_client):
        response = self.client.post(self.url, {"username": "", "confirmation_code": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Username and confirmation code are required.", [str(m) for m in messages]
        )

    @patch("boto3.client")
    def test_successful_confirmation(self, mock_boto3_client):
        mock_boto3_client.return_value.confirm_sign_up.return_value = {}
        response = self.client.post(
            self.url, {"username": "testuser", "confirmation_code": "123456"}
        )
        self.assertRedirects(response, reverse("login"))
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Your account has been confirmed. Please log in.",
            [str(m) for m in messages],
        )

    @patch("boto3.client")
    def test_confirmation_code_mismatch(self, mock_boto3_client):
        mock_boto3_client.return_value.confirm_sign_up.side_effect = ClientError(
            {
                "Error": {
                    "Code": "CodeMismatchException",
                    "Message": "Invalid confirmation code",
                }
            },
            "confirm_sign_up",
        )
        response = self.client.post(
            self.url, {"username": "testuser", "confirmation_code": "wrongcode"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Invalid confirmation code. Please try again.", [str(m) for m in messages]
        )

    @patch("boto3.client")
    def test_confirmation_code_expired(self, mock_boto3_client):
        mock_boto3_client.return_value.confirm_sign_up.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ExpiredCodeException",
                    "Message": "Confirmation code expired",
                }
            },
            "confirm_sign_up",
        )
        response = self.client.post(
            self.url, {"username": "testuser", "confirmation_code": "expiredcode"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "Confirmation code expired. Please request a new code.",
            [str(m) for m in messages],
        )

    def test_get_request(self):
        # Test handling of GET request
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm.html")


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.profile_url = reverse("profile")
        self.client = Client()
        self.client.login(username="testuser", password="password")

    @patch("boto3.client")
    def test_profile_view_authenticated(self, mock_boto3_client):
        normal_response = {
            "UserAttributes": [
                {"Name": "given_name", "Value": "John"},
                {"Name": "family_name", "Value": "Doe"},
                {"Name": "email", "Value": "john.doe@example.com"},
            ]
        }

        exception_response = ClientError(
            {
                "Error": {
                    "Code": "NotAuthorizedException",
                    "Message": "Password attempts exceeded",
                }
            },
            "AdminGetUser",
        )

        mock_boto3_client.return_value.admin_get_user.side_effect = [
            normal_response,
            exception_response,
        ]

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")
        context = response.context
        self.assertEqual(context["first_name"], "John")

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Failed to retrieve profile information" in str(m) for m in messages)
        )
        self.assertTrue(any("Password attempts exceeded" in str(m) for m in messages))

    def test_profile_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f"/login/?next={self.profile_url}")


class CognitoBackendTestCase(TestCase):
    def setUp(self):
        self.backend = CognitoBackend()

    @patch("taxiapp.cognito_backend.CognitoBackend.get_or_create_user")
    @patch("taxiapp.cognito_backend.CognitoBackend.verify_token")
    @patch("taxiapp.cognito_backend.CognitoBackend.get_secret_hash")
    @patch("taxiapp.cognito_backend.boto3.client")
    def test_authenticate_success(
        self,
        mock_boto3_client,
        mock_get_secret_hash,
        mock_verify_token,
        mock_get_or_create_user,
    ):
        mock_get_secret_hash.return_value = "mocked_secret_hash"
        mock_boto3_client.return_value.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "dummy_token"}
        }
        mock_verify_token.return_value = {
            "username": "testuser",
            "email": "test@example.com",
        }
        mock_get_or_create_user.return_value = User(username="testuser")
        user = self.backend.authenticate(None, username="testuser", password="testpass")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        mock_boto3_client.return_value.admin_initiate_auth.assert_called_once_with(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": "testuser",
                "PASSWORD": "testpass",
                "SECRET_HASH": "mocked_secret_hash",
            },
        )
        mock_verify_token.assert_called_once_with("dummy_token")
        mock_get_or_create_user.assert_called_once_with(
            {"username": "testuser", "email": "test@example.com"}, "testuser"
        )

    @patch("taxiapp.cognito_backend.boto3.client")
    def test_authenticate_failure(self, mock_boto3_client):
        mock_boto3_client.return_value.admin_initiate_auth.side_effect = Exception(
            "Authentication failed"
        )
        user = self.backend.authenticate(
            None, username="testuser", password="wrongpass"
        )
        self.assertIsNone(user)

    @patch("taxiapp.cognito_backend.boto3.client")
    def test_initiate_auth(self, mock_boto3_client):
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "dummy_token"}
        }

        backend = CognitoBackend()
        result = backend.initiate_auth(
            mock_client, "testuser", "testpass", "mocked_secret_hash"
        )

        self.assertEqual(result, {"AuthenticationResult": {"IdToken": "dummy_token"}})
        mock_client.admin_initiate_auth.assert_called_once_with(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": "testuser",
                "PASSWORD": "testpass",
                "SECRET_HASH": "mocked_secret_hash",
            },
        )

    @patch("taxiapp.cognito_backend.User.objects.get")
    @patch("taxiapp.cognito_backend.User.objects.create_user")
    def test_get_or_create_user(self, mock_create_user, mock_get):
        username = "testuser"
        email = "test@example.com"
        given_name = "Test"
        family_name = "User"

        mock_get.side_effect = User.DoesNotExist

        mock_create_user.return_value = User.objects.create(
            username=username, email=email, first_name=given_name, last_name=family_name
        )

        claims = {
            "username": username,
            "email": email,
            "given_name": given_name,
            "family_name": family_name,
        }

        user = self.backend.get_or_create_user(claims, username)

        mock_get.assert_called_once_with(username=username)
        mock_create_user.assert_called_once_with(
            username=username, email=email, first_name=given_name, last_name=family_name
        )

        self.assertEqual(user.username, username)
        self.assertEqual(user.email, email)
        self.assertEqual(user.first_name, given_name)
        self.assertEqual(user.last_name, family_name)

    def test_get_user(self):
        test_user = User.objects.create_user(username="testuser", password="testpass")
        user = self.backend.get_user(test_user.id)
        self.assertEqual(user, test_user)

    def test_get_user_not_exist(self):
        user = self.backend.get_user(999)
        self.assertIsNone(user)

    @patch("taxiapp.cognito_backend.settings.COGNITO_APP_CLIENT_ID", "test_client_id")
    @patch(
        "taxiapp.cognito_backend.settings.COGNITO_APP_CLIENT_SECRET",
        "test_client_secret",
    )
    def test_get_secret_hash(self):
        username = "testuser"
        message = username + settings.COGNITO_APP_CLIENT_ID
        dig = hmac.new(
            settings.COGNITO_APP_CLIENT_SECRET.encode("UTF-8"),
            msg=message.encode("UTF-8"),
            digestmod=hashlib.sha256,
        ).digest()
        expected_hash = base64.b64encode(dig).decode()

        secret_hash = self.backend.get_secret_hash(username)

        self.assertEqual(secret_hash, expected_hash)


class ASGITest(TestCase):
    def test_asgi_application(self):
        client = Client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
