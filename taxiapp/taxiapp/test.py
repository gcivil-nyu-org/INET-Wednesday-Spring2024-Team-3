from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from user.models import FriendRequest, Friendship
from forum.models import Post, Comment
from unittest.mock import patch
from taxiapp.cognito_backend import CognitoBackend

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

    def test_register_view_post_success(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'full_name': 'New User'
        })
        self.assertRedirects(response, '/confirm/')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_profile_view_authenticated(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_profile_view_unauthenticated(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, '/accounts/login/?next=/profile')

    def tearDown(self):
        self.user.delete()

class CognitoBackendTestCase(TestCase):
    def setUp(self):
        self.backend = CognitoBackend()

    @patch('taxiapp.cognito_backend.boto3.client')
    @patch('taxiapp.cognito_backend.requests.get')
    def test_authenticate_success(self, mock_requests_get, mock_boto3_client):
        # Mock the Cognito response
        mock_boto3_client.return_value.admin_initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "dummy_token"}
        }

        # Mock the JWKS response
        mock_requests_get.return_value.json.return_value = {"keys": [{"kty": "RSA", "n": "dummy_n", "e": "dummy_e"}]}

        # Call the authenticate method
        user = self.backend.authenticate(None, username='testuser', password='testpass')

        # Check if the user was created
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')

    @patch('taxiapp.cognito_backend.boto3.client')
    def test_authenticate_failure(self, mock_boto3_client):
        # Mock the Cognito response to raise an exception
        mock_boto3_client.return_value.admin_initiate_auth.side_effect = Exception('Authentication failed')

        # Call the authenticate method
        user = self.backend.authenticate(None, username='testuser', password='wrongpass')

        # Check if the user is None
        self.assertIsNone(user)

    def test_get_user(self):
        # Create a test user
        test_user = User.objects.create_user(username='testuser', password='testpass')

        # Retrieve the user using the backend
        user = self.backend.get_user(test_user.id)

        # Check if the correct user was retrieved
        self.assertEqual(user, test_user)

    def test_get_user_not_exist(self):
        # Attempt to retrieve a user that does not exist
        user = self.backend.get_user(999)

        # Check if the result is None
        self.assertIsNone(user)