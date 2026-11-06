import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
import dj_database_url # ✅ Import ajouté pour Render

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Chargement des variables d'environnement ---
try:
    from dotenv import load_dotenv

    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✅ Fichier .env chargé depuis : {env_path}")
    else:
        print(f"⚠️ Fichier .env NON TROUVÉ à l'emplacement : {env_path}")
except ImportError:
    print("⚠️ python-dotenv n'est pas installé (pip install python-dotenv).")


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


# --- SECRETS & MODE ---
DEBUG = _env_bool('DJANGO_DEBUG', False)

SECRET_KEY = (os.environ.get('DJANGO_SECRET_KEY') or '').strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
        print('⚠️ DJANGO_SECRET_KEY absente : clé aléatoire temporaire générée.')
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY n'est pas définie. Ajoute-la dans backend/.env"
        )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]
# ✅ AJOUT POUR RENDER : On autorise Render par défaut
if os.environ.get('RENDER'):
    ALLOWED_HOSTS.append(os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''))


# --- APPS INSTALLÉES ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',

    'apps.users',
    'apps.claims',
    'apps.attachments',
    'apps.notifications',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # ✅ AJOUT WHITENOISE
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- BASE DE DONNÉES POSTGRESQL ---
# ✅ On utilise dj_database_url pour basculer entre local et production automatiquement
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600
    )
}

# --- VALIDATEURS ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNATIONALISATION ---
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Nouakchott'
USE_I18N = True
USE_TZ = True

# --- FICHIERS STATIQUES ET MEDIA ---
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ Configuration WhiteNoise pour la production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['*']
CORS_ALLOW_METHODS = ['*']

# --- REST FRAMEWORK & JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 500,
    'DEFAULT_THROTTLE_RATES': {
        'sms_reset': '20/hour',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

AUTHENTICATION_BACKENDS = [
    'apps.users.backends.EmailOrPhoneModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# --- EMAIL (SENDLIBERTY API) ---
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
SENDLIBERTY_API_KEY = os.environ.get('SENDLIBERTY_API_KEY', '').strip()
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Sawtak <aishaaliou2012@gmail.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL


def _check_email_config():
    if not SENDLIBERTY_API_KEY:
        print('⚠️ SENDLIBERTY : SENDLIBERTY_API_KEY manquante dans le .env — aucun email ne partira.')
    else:
        print(f'✅ SENDLIBERTY : Clé API chargée pour l\'expéditeur {DEFAULT_FROM_EMAIL}')


_check_email_config()

# --- CHINQIT (SMS pour la Mauritanie) ---
CHINQIT_API_KEY = os.environ.get('CHINQIT_API_KEY', '').strip()

if not CHINQIT_API_KEY:
    print('⚠️ CHINQIT : CHINQIT_API_KEY manquante — la réinitialisation par SMS échouera.')

# --- FIREBASE (notifications push FCM) ---
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    'FIREBASE_CREDENTIALS_PATH',
    os.path.join(BASE_DIR, 'serviceAccountKey.json'),
)

if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
    print(f'⚠️ FIREBASE : {FIREBASE_CREDENTIALS_PATH} introuvable — aucun push ne partira.')
else:
    print('✅ FIREBASE : clé de service trouvée.')

# --- LOGS ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}