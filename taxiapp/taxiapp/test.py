from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from user.models import FriendRequest, Friendship
from forum.models import Post, Comment
from taxiapp.views import get_secret_hash
from unittest.mock import patch, MagicMock
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

    def test_register_view_get(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "register.html")

    @patch("boto3.client")
    def test_register_view_post_success(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.return_value = {
            "UserConfirmed": True,
        }

        response = self.client.post(
            reverse("register"),
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
    def test_register_view_post_username_exists(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.side_effect = [
            ClientError(
                {
                    "Error": {
                        "Code": "UsernameExistsException",
                        "Message": "Username already exists",
                    }
                },
                "operation_name",
            ),
        ]

        response = self.client.post(
            reverse("register"),
            {
                "username": "existinguser",
                "email": "existinguser@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "full_name": "Existing User",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(get_messages(response.wsgi_request)), 1)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("error" in message.tags for message in messages))
        self.assertContains(response, "A user with this username already exists.")

    @patch("boto3.client")
    def test_register_view_post_error(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.side_effect = [
            ClientError(
                {"Error": {"Code": "SomeOtherError", "Message": "Some other error"}},
                "operation_name",
            ),
        ]

        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "full_name": "New User",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(get_messages(response.wsgi_request)), 1)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("error" in message.tags for message in messages))
        self.assertContains(response, "An error occurred: Some other error")

    def test_profile_view_authenticated(self):
        self.client.login(username="testuser", password="12345")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")

    def test_profile_view_unauthenticated(self):
        response = self.client.get("/profile/")
        self.assertRedirects(response, "/login/?next=/profile/")

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

    @patch("taxiapp.views.get_secret_hash", return_value="fake_secret_hash")
    @patch("taxiapp.views.boto3.client")
    def test_reset_view(self, mock_boto3_client, mock_get_secret_hash):
        mock_client_instance = mock_boto3_client.return_value

        mock_client_instance.forgot_password.return_value = {}

        response = self.client.post(
            reverse("reset"),
            data={"user_identifier": "test@example.com", "request_reset": "true"},
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response, "Password reset code sent. Please check your email."
        )

        mock_client_instance.forgot_password.assert_called_once_with(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username="test@example.com",
            SecretHash="fake_secret_hash",
        )

        with patch("django.contrib.messages.error") as mock_messages_error:

            response = self.client.post(
                reverse("reset"),
                data={
                    "username": "test@example.com",
                    "verification_code": "123456",
                    "new_password": "new_password",
                    "confirm_reset": "true",
                },
            )

            self.assertEqual(response.status_code, 302)

            mock_messages_error.assert_not_called()

            mock_client_instance.confirm_forgot_password.assert_called_once_with(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                SecretHash="fake_secret_hash",
                Username="test@example.com",
                ConfirmationCode="123456",
                Password="new_password",
            )

        def test_faq_view(self):
            response = self.client.get(reverse("faq"))
            self.assertEqual(response.status_code, 200)

            faq_data = [
                {
                    "question": "How do I sign up for an account?",
                    "answer": "You can sign up by clicking the 'Register' button on the homepage and filling in the required information.",
                },
            ]

            for faq_item in faq_data:
                self.assertContains(response, faq_item["question"])
                self.assertContains(response, faq_item["answer"])


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
