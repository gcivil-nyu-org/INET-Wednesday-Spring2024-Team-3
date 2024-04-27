from pathlib import Path
import environ
import os
import botocore
import botocore.session
import boto3
from botocore.exceptions import ClientError
import json


def get_secret(name):
    secret_name = "taxiapp_secrets"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(f"Failed to retrieve secret '{secret_name}': {e}")
        return None

    secret = get_secret_value_response.get("SecretString")
    if not secret:
        print(f"Secret '{secret_name}' does not contain a string value.")
        return None
    secret_dict = json.loads(secret)
    api_key = secret_dict.get(name)
    os.environ[name] = api_key
    return api_key


SECRET_KEY = get_secret("SECRET_KEY")
COGNITO_DOMAIN = get_secret("COGNITO_DOMAIN")
COGNITO_APP_CLIENT_SECRET = get_secret("COGNITO_APP_CLIENT_SECRET")
COGNITO_USER_POOL_ID = "us-east-1_xjtJDp8bd"
os.environ[COGNITO_USER_POOL_ID] = COGNITO_USER_POOL_ID
COGNITO_APP_CLIENT_ID = get_secret("COGNITO_APP_CLIENT_ID")
COGNITO_AWS_REGION = get_secret("COGNITO_AWS_REGION")
COGNITO_PUBLIC_KEYS_URL = f"https://cognito-idp.{COGNITO_AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
os.environ[COGNITO_PUBLIC_KEYS_URL] = COGNITO_PUBLIC_KEYS_URL
GOOGLE_MAPS_API_KEY = get_secret("GOOGLE_MAPS_API_KEY")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ##########Uncomment for local development, add secrets.env local file###############
# env = environ.Env()
# environ.Env.read_env(env_file="secrets.env")
# SECRET_KEY = env("SECRET_KEY")


# # SECURITY WARNING: keep the secret key used in production secret!
# COGNITO_DOMAIN = env("COGNITO_DOMAIN")
# COGNITO_APP_CLIENT_SECRET = env("COGNITO_APP_CLIENT_SECRET")
# COGNITO_USER_POOL_ID = env("COGNITO_USER_POOL_ID")
# COGNITO_APP_CLIENT_ID = env("COGNITO_APP_CLIENT_ID")
# COGNITO_AWS_REGION = env("COGNITO_AWS_REGION")
# GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY")

# KEEPING THIS?
# UBER_CLIENT_ID = env("UBER_CLIENT_ID")
# UBER_CLIENT_SECRET = env("UBER_CLIENT_SECRET")
# LYFT_API_KEY = env("LYFT_API_KEY")

# # # #############Uncomment for travis deployment##############
# SECRET_KEY = os.environ.get("SECRET_KEY")
# COGNITO_DOMAIN = os.environ.get("COGNITO_DOMAIN")
# COGNITO_APP_CLIENT_SECRET = os.environ.get("COGNITO_APP_CLIENT_SECRET")
# OGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
# COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")
# COGNITO_AWS_REGION = os.environ.get("COGNITO_AWS_REGION")
# GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
# COGNITO_PUBLIC_KEYS_URL = f"https://cognito-idp.{COGNITO_AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

# ##########################################################

# In the future, add this as travis variables to protect URL.
AWS_STORAGE_BUCKET_NAME = "taxiapp-static-bucket"
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
STATIC_LOCATION = "static"  # I don't know if we need this
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["127.0.0.1", "taxiapp2.us-east-1.elasticbeanstalk.com"]


# Application definition

AUTHENTICATION_BACKENDS = [
    "taxiapp.cognito_backend.CognitoBackend",
    "django.contrib.auth.backends.ModelBackend",
]


INSTALLED_APPS = [
    "taxiapp",
    "forum",
    "rideshare",
    "user",
    "tools",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "forum.middleware.RedirectIfPostNotFoundMiddleware",
]

ROOT_URLCONF = "taxiapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "taxiapp", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "taxiapp.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "US/Eastern"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}
