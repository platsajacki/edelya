from datetime import timedelta
from os import getenv
from pathlib import Path

from corsheaders.defaults import default_headers
from dotenv import load_dotenv

from core.logging_handlers import get_logging_dict
from core.utils import build_redis_retry_policy

load_dotenv()

# Base settings for the Django project.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = getenv('SECRET_KEY', 'django-insecure-default-key')

DEBUG = bool(int(getenv('DEBUG', 0)))

ALLOWED_HOSTS = getenv('ALLOWED_HOSTS', '').split(', ')
CORS_ALLOWED_ORIGINS = getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173, http://127.0.0.1:5173').split(', ')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-tg-init-data',
]
CSRF_TRUSTED_ORIGINS = getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1').split(', ')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
LOCAL_APPS = [
    'apps.a12n',
    'apps.dishes',
    'apps.planning',
    'apps.shopping',
    'apps.subscriptions',
    'apps.users',
]
THIRD_PARTY_APPS = [
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'rest_framework',
    'rest_framework_simplejwt',
]
INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

WSGI_APPLICATION = 'core.wsgi.application'


# Database
ENGINE = 'core.backends.db.postgresql'

DATABASES = {
    'default': {
        'ENGINE': ENGINE,
        'NAME': getenv('POSTGRES_DB', 'edelya'),
        'USER': getenv('POSTGRES_USER', 'user'),
        'PASSWORD': getenv('POSTGRES_PASSWORD', 'password'),
        'HOST': getenv('POSTGRES_HOST', 'localhost'),
        'PORT': getenv('POSTGRES_PORT', '5432'),
    }
}
MAX_DB_CONNECTION_RETRIES = int(getenv('MAX_DB_CONNECTION_RETRIES', '3'))
DELAY_BETWEEN_DB_RETRIES = float(getenv('DELAY_BETWEEN_DB_RETRIES', '0.2'))

# Password validation
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

AUTH_USER_MODEL = 'users.User'


# Telegram Bot settings
EDELYA_BOT_TOKEN = getenv('EDELYA_BOT_TOKEN', '')

# Frontend URL
FRONTEND_URL = getenv('FRONTEND_URL', '')

# YooKassa settings
YOOKASSA_SHOP_ID = getenv('YOOKASSA_SHOP_ID', '')
YOOKASSA_SECRET_KEY = getenv('YOOKASSA_SECRET_KEY', '')
YOOKASSA_RETURN_URL = f'{FRONTEND_URL.rstrip("/")}/#/cabinet?payment_return=1' if FRONTEND_URL else ''

# Rest Framework & JWT settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('apps.a12n.authentications.JWTAuthenticationWithSubscription',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# Redis and Celery Settings
REDIS_HOST = getenv('REDIS_HOST', 'redis://127.0.0.1:6379')
REDIS_TOTAL_CONNECTION_ATTEMPTS = int(getenv('REDIS_TOTAL_CONNECTION_ATTEMPTS', '5'))
REDIS_SOCKET_CONNECT_TIMEOUT = float(getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '2'))
REDIS_SOCKET_TIMEOUT = float(getenv('REDIS_SOCKET_TIMEOUT', '3'))
REDIS_RETRY_BACKOFF_BASE = float(getenv('REDIS_RETRY_BACKOFF_BASE', '0.3'))
REDIS_RETRY_BACKOFF_CAP = float(getenv('REDIS_RETRY_BACKOFF_CAP', '1.5'))
REDIS_RETRY_POLICY = build_redis_retry_policy(
    attempts=REDIS_TOTAL_CONNECTION_ATTEMPTS, base=REDIS_RETRY_BACKOFF_BASE, cap=REDIS_RETRY_BACKOFF_CAP
)

REDIS_CACHE_OPTIONS = {
    'socket_connect_timeout': REDIS_SOCKET_CONNECT_TIMEOUT,
    'socket_timeout': REDIS_SOCKET_TIMEOUT,
    'retry_on_timeout': True,
    'retry': REDIS_RETRY_POLICY,
}

REDIS_CELERY_RETRY_POLICY = {
    'interval_start': 0,
    'interval_step': REDIS_RETRY_BACKOFF_BASE,
    'interval_max': REDIS_RETRY_BACKOFF_CAP,
    'max_retries': REDIS_TOTAL_CONNECTION_ATTEMPTS,
}

if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f'{REDIS_HOST}/1',
            'OPTIONS': REDIS_CACHE_OPTIONS,
        }
    }
    CELERY_BROKER_URL = f'{REDIS_HOST}/2'
    CELERY_BACKEND_URL = f'{REDIS_HOST}/3'
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_RESULT_EXPIRES = 3600
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
    CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    CELERYD_MAX_TASKS_PER_CHILD = 100
    CELERYD_PREFETCH_MULTIPLIER = 4
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'max_retries': REDIS_TOTAL_CONNECTION_ATTEMPTS,
        'retry_policy': REDIS_CELERY_RETRY_POLICY,
    }


# logging configuration
LOKI_CONTAINER = getenv('LOKI_CONTAINER', 'loki.loki.svc.cluster.local:3100')
LOKI_APP_NAME = getenv('LOKI_APP_NAME', 'dev_edelya_backend')

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = get_logging_dict(
    log_formatter='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datetime_formatter='%Y-%m-%d %H:%M:%S',
    log_dir=LOG_DIR,
    loki_container=LOKI_CONTAINER,
    loki_app_name=LOKI_APP_NAME,
    debug=DEBUG,
)
