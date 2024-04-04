import hmac
import hashlib
import base64
import logging
from django.conf import settings
import boto3
import requests
from authlib.jose import JsonWebKey, jwt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class CognitoBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        client = boto3.client("cognito-idp", region_name=settings.COGNITO_AWS_REGION)
        try:
            secret_hash = self.get_secret_hash(username)
            result = self.initiate_auth(client, username, password, secret_hash)
            id_token = result["AuthenticationResult"]["IdToken"]
            claims = self.verify_token(id_token)
            if claims:
                return self.get_or_create_user(claims, username)
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None

    def initiate_auth(self, client, username, password, secret_hash):
        return client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": secret_hash,
            },
        )

    def verify_token(self, id_token):
        jwks = requests.get(settings.COGNITO_PUBLIC_KEYS_URL).json()
        key = JsonWebKey.import_key_set(jwks)
        claims = jwt.decode(id_token, key)
        try:
            claims.validate(leeway=60)  # 60 seconds leeway for clock skew
            return claims
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            return None

    def get_or_create_user(self, claims, username):
        email = claims.get("email")
        given_name = claims.get("given_name")
        family_name = claims.get("family_name")
        try:
            user = User.objects.get(username=username)
            # Update user attributes if they have changed in Cognito
            if (
                user.email != email
                or user.first_name != given_name
                or user.last_name != family_name
            ):
                user.email = email
                user.first_name = given_name
                user.last_name = family_name
                user.save()
        except ObjectDoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=given_name,
                last_name=family_name,
            )
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_secret_hash(username):
        message = username + settings.COGNITO_APP_CLIENT_ID
        dig = hmac.new(
            settings.COGNITO_APP_CLIENT_SECRET.encode("UTF-8"),
            msg=message.encode("UTF-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(dig).decode()
