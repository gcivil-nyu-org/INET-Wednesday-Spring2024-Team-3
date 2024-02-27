import hmac
import hashlib
import base64
from django.conf import settings
import boto3
import requests
from authlib.jose import JsonWebKey, jwt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


class CognitoBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        client = boto3.client('cognito-idp', region_name=settings.COGNITO_AWS_REGION)
        try:
            secret_hash = self.get_secret_hash(username, settings.COGNITO_APP_CLIENT_ID, settings.COGNITO_APP_CLIENT_SECRET)

            result = client.admin_initiate_auth(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash
                }
            )
            id_token = result['AuthenticationResult']['IdToken']
            # Fetch the JWKs 
            jwks = requests.get(settings.COGNITO_PUBLIC_KEYS_URL).json()
            key = JsonWebKey.import_key_set(jwks)
            claims = jwt.decode(id_token, key)
            try:
                claims.validate(leeway=60)  # 60 seconds leeway for clock skew
            except Exception as e:
                print(f"Validation failed: {str(e)}")

            # Extract required attributes
            email = claims.get('email')
            given_name = claims.get('given_name')
            family_name = claims.get('family_name')

            # Logic to create or get a Django user
            try:
                user = User.objects.get(username=username)
            except ObjectDoesNotExist:
                # If user does not exist, create a new user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=given_name,
                    last_name=family_name
                )
                user.save()

            return user
        except Exception as e:
            # Handle exceptions
            print(f"Authentication failed: {str(e)}") 
            return None

    @staticmethod
    def get_secret_hash(username, client_id, client_secret):
        message = username + client_id
        dig = hmac.new(client_secret.encode('UTF-8'),
                       msg=message.encode('UTF-8'),
                       digestmod=hashlib.sha256).digest()
        return base64.b64encode(dig).decode()
