from unittest import mock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from user.models import FriendRequest, Friendship
from forum.models import Post, Comment
from unittest.mock import patch, MagicMock
from taxiapp.cognito_backend import CognitoBackend
from django.conf import settings

class ViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_post_success(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': '12345'})
        self.assertRedirects(response, '/')

    def test_login_view_post_failure(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Invalid credentials' in response.context['error'])

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    @patch('boto3.client')
    def test_register_view_post_success(self, mock_boto3_client):
        mock_boto3_client.return_value.sign_up.return_value = {
            'UserConfirmed': True,
        }

        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'full_name': 'New User'
        })

        self.assertRedirects(response, reverse('confirm'))

    def test_profile_view_authenticated(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_profile_view_unauthenticated(self):
        response = self.client.get('/profile/')
        self.assertRedirects(response, '/login/?next=/profile/')

    def tearDown(self):
        self.user.delete()

class CognitoBackendTestCase(TestCase):
    def setUp(self):
        self.backend = CognitoBackend()

    @patch('taxiapp.cognito_backend.CognitoBackend.get_or_create_user')
    @patch('taxiapp.cognito_backend.CognitoBackend.verify_token')
    @patch('taxiapp.cognito_backend.CognitoBackend.get_secret_hash')
    @patch('taxiapp.cognito_backend.boto3.client')
    def test_authenticate_success(self, mock_boto3_client, mock_get_secret_hash, mock_verify_token, mock_get_or_create_user):
        mock_get_secret_hash.return_value = 'mocked_secret_hash'
        mock_boto3_client.return_value.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "dummy_token"}
        }
        mock_verify_token.return_value = {"username": "testuser", "email": "test@example.com"}
        mock_get_or_create_user.return_value = User(username='testuser')
        user = self.backend.authenticate(None, username='testuser', password='testpass')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        mock_boto3_client.return_value.admin_initiate_auth.assert_called_once_with(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": 'testuser',
                "PASSWORD": 'testpass',
                "SECRET_HASH": 'mocked_secret_hash'
            },
        )
        mock_verify_token.assert_called_once_with('dummy_token')
        mock_get_or_create_user.assert_called_once_with({"username": "testuser", "email": "test@example.com"}, 'testuser')

    @patch('taxiapp.cognito_backend.boto3.client')
    def test_authenticate_failure(self, mock_boto3_client):
        mock_boto3_client.return_value.admin_initiate_auth.side_effect = Exception('Authentication failed')
        user = self.backend.authenticate(None, username='testuser', password='wrongpass')
        self.assertIsNone(user)

    def test_get_user(self):
        test_user = User.objects.create_user(username='testuser', password='testpass')
        user = self.backend.get_user(test_user.id)
        self.assertEqual(user, test_user)

    def test_get_user_not_exist(self):
        user = self.backend.get_user(999)
        self.assertIsNone(user)