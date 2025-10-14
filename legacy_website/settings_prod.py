"""
Django production settings for legacy_website project.
This file is used for the Render deployment environment.
"""

from pathlib import Path
import os
import dj_database_url
import cloudinary

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = 'django-insecure-h*(dfrl3dit^30qbe=v5+10j4-ns*_bt)k5uu84%$ma4%a2-1z'

# CRITICAL CHANGE: Set DEBUG to False for production
DEBUG = False


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Ensure all hosts are single strings separated by commas
ALLOWED_HOSTS = ['*']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition (INSTALLED_APPS, MIDDLEWARE, ROOT_URLCONF, TEMPLATES, WSGI_APPLICATION remain the same)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main_app',
    'cloudinary_storage',
    'cloudinary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
# CRITICAL CHANGE: Remove the 'default=...' SQLite fallback.
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        conn_max_age=600,
    )
}

# ... (Password validation, Internationalization remain the same) ...


# STATIC FILE CONFIGURATION (WhiteNoise)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'main_app' / 'static',
]


# MEDIA FILE STORAGE (CLOUDINARY) - Configuration remains the same
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MEDIA_URL = '/media/'
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

CLOUDINARY_URL = 'cloudinary://{}:{}@{}'.format(
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME
)
CLOUDINARY_API_SECURE = True


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = '/login/'



INSTAGRAM_VERIFY_TOKEN = 'Gyan2025SecretToken'



# === INSTAGRAM INTEGRATION SETTINGS ===

# [1] Your Meta App ID (from Settings -> Basic)
INSTAGRAM_APP_ID = '692028360605970'  # Your App ID

# [2] Your Meta App Secret (from Settings -> Basic - Click 'Show')
INSTAGRAM_APP_SECRET = 'fd1bfc72abdaa0e2efc74a386525ce82' # You must paste your App Secret

# [3] The EXACT Redirect URI you set in Meta Developer Dashboard
INSTAGRAM_REDIRECT_URI = 'https://gyan.pythonanywhere.com/auth/instagram/callback/'