"""
Django settings for legacy_website project.
"""

from pathlib import Path
import os
import dj_database_url # For parsing the Render DATABASE_URL
import cloudinary # CRITICAL: MUST BE AT THE TOP FOR CONFIGURATION

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CLOUDINARY INITIALIZATION FIX ---
# This block ensures the Cloudinary library initializes itself immediately
# using the CLOUDINARY_URL environment variable, resolving the 404 image issue.
if os.environ.get('CLOUDINARY_URL'):
    cloudinary.config(
        secure=True
    )
# --------------------------------------

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-h*(dfrl3dit^30qbe=v5+10j4-ns*_bt)k5uu84%$ma4%a2-1z'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Ensure all hosts are single strings separated by commas
ALLOWED_HOSTS = ['*']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main_app',
    'cloudinary_storage', # New
    'cloudinary',         # New
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ADDED WHITE NOISE HERE
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'legacy_website.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'legacy_website.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
   'default': dj_database_url.config(
        # CRITICAL: Looks for the DATABASE_URL environment variable from Render
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        engine='django.db.backends.postgresql'
    )
}


# Password validation... (your original settings are here)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization... (your original settings are here)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# -------------------------------------------------------------
# STATIC FILE CONFIGURATION (WhiteNoise)
# -------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'main_app' / 'static',
]


# -------------------------------------------------------------
# MEDIA FILE STORAGE (CLOUDINARY) - FINAL CLEAN CONFIG
# -------------------------------------------------------------

# 1. Tell Django to use Cloudinary for all file storage.
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 2. CRITICAL: Pass the URL to the library for initialization.
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

# 3. Ensure images are served securely.
CLOUDINARY_API_SECURE = True

# NOTE: MEDIA_URL and MEDIA_ROOT are removed/commented to prevent conflict.

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = '/login/'