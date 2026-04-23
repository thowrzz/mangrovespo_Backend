from pathlib import Path
from decouple import config, Csv
import dj_database_url
from datetime import timedelta
import os

BASE_DIR   = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_OAUTH_CLIENT_ID', default='')

DJANGO_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles']
THIRD_PARTY_APPS = ['rest_framework','rest_framework_simplejwt','corsheaders','django_filters','cloudinary','cloudinary_storage','django_celery_beat']
LOCAL_APPS = ['apps.activities.apps.ActivitiesConfig','apps.bookings.apps.BookingsConfig','apps.payments.apps.PaymentsConfig','apps.availability.apps.AvailabilityConfig','apps.notifications.apps.NotificationsConfig','apps.reports.apps.ReportsConfig','customer_auth']
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware','django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = config('EMAIL_HOST_USER')

DATABASES = {'default': dj_database_url.parse(config('DATABASE_URL', default='sqlite:///db.sqlite3'), conn_max_age=600, conn_health_checks=True)}

AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

STATIC_URL          = '/static/'
STATIC_ROOT         = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD  = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS   = config('CORS_ALLOWED_ORIGINS', cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['accept','accept-encoding','authorization','content-type','dnt','origin','user-agent','x-csrftoken','x-requested-with']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('customer_auth.authentication.CustomerJWTAuthentication','rest_framework_simplejwt.authentication.JWTAuthentication'),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend','rest_framework.filters.SearchFilter','rest_framework.filters.OrderingFilter'),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME':timedelta(days=7),'REFRESH_TOKEN_LIFETIME':timedelta(days=30),'ROTATE_REFRESH_TOKENS':True,'AUTH_HEADER_TYPES':('Bearer',)}

RAZORPAY_KEY_ID         = config('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET     = config('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')

CLOUDINARY_STORAGE = {'CLOUD_NAME':config('CLOUDINARY_CLOUD_NAME'),'API_KEY':config('CLOUDINARY_API_KEY'),'API_SECRET':config('CLOUDINARY_API_SECRET')}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
import cloudinary
cloudinary.config(cloud_name=config('CLOUDINARY_CLOUD_NAME'),api_key=config('CLOUDINARY_API_KEY'),api_secret=config('CLOUDINARY_API_SECRET'),secure=True)

ADMIN_EMAIL              = config('ADMIN_EMAIL', default='mangrovespot.care@gmail.com')
FRONTEND_URL             = config('FRONTEND_URL', default='http://localhost:3000')
SLOT_HOLD_MINUTES        = 15
BOOKING_REFERENCE_PREFIX = 'MS'

CELERY_BROKER_URL                         = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND                     = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TIMEZONE                           = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER                     = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE             = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SERIALIZER            = 'json'
CELERY_RESULT_SERIALIZER          = 'json'
CELERY_ACCEPT_CONTENT             = ['json']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
