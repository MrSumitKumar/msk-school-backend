from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import os
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────
# Core Settings
# ─────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='change-this-secret-key')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# ─────────────────────────────────────────
# Applications
# ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'rest_framework',

    # Local apps
    'accounts',
    'schools',
    'academics',
    'students',
    'teachers',
    'attendance',
    'fees',
    'exams',
    'timetable',
    'audit',
]

# ─────────────────────────────────────────
# Middleware (⚠️ ORDER FIXED)
# ─────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',      # MUST be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─────────────────────────────────────────
# URLs / WSGI
# ─────────────────────────────────────────
ROOT_URLCONF = 'schoolsaas.urls'
WSGI_APPLICATION = 'schoolsaas.wsgi.application'

# ─────────────────────────────────────────
# Database (SQLite / MySQL switch)
# ─────────────────────────────────────────
USE_MYSQL = config('USE_MYSQL', default=False, cast=bool)

if USE_MYSQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='3306'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─────────────────────────────────────────
# Auth
# ─────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─────────────────────────────────────────
# Localization
# ─────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────
# Static & Media
# ─────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# ─────────────────────────────────────────
# Django REST Framework
# ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'accounts.permissions.GlobalTenantPermission',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─────────────────────────────────────────
# JWT
# ─────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─────────────────────────────────────────
# CORS (FIXED & CLEAN)
# ─────────────────────────────────────────
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
    ]
else:
    CORS_ALLOWED_ORIGINS = [
        "https://msk-school-frontend.vercel.app",
    ]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization',
    'content-type',
]
# ─────────────────────────────────────────
# CSRF
# ─────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    "https://msk-school-frontend.vercel.app",
]

# ─────────────────────────────────────────
# Payment Gateways
# ─────────────────────────────────────────
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

PHONEPE_MERCHANT_ID = config('PHONEPE_MERCHANT_ID', default='')
PHONEPE_SALT_KEY = config('PHONEPE_SALT_KEY', default='')
PHONEPE_SALT_INDEX = config('PHONEPE_SALT_INDEX', default='1')
PHONEPE_API_URL = config('PHONEPE_API_URL', default='https://api-preprod.phonepe.com/apis/hermes/pg/v1/pay')

BINANCE_API_KEY = config('BINANCE_API_KEY', default='')
BINANCE_API_SECRET = config('BINANCE_API_SECRET', default='')
BINANCE_API_URL = config('BINANCE_API_URL', default='https://bpay.binanceapi.com/binancepay/openapi/v2/order')