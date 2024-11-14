#!/bin/bash

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setup ambiente di sviluppo CerCollettiva${NC}"
echo "----------------------------------------"

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 non trovato. Installazione...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# Verifica Poetry
if ! command -v poetry &> /dev/null; then
    echo -e "${BLUE}Installazione Poetry...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Creazione directory progetto
echo -e "${BLUE}Creazione directory progetto...${NC}"
mkdir -p cercollettiva
cd cercollettiva

# Inizializzazione poetry e ambiente virtuale
echo -e "${BLUE}Inizializzazione Poetry...${NC}"
poetry init --name "cercollettiva" \
    --description "Software opensource per la gestione delle comunità energetiche" \
    --author "Your Name <your.email@example.com>" \
    --python "^3.9" \
    --dependency "django@^4.2" \
    --dependency "python-dotenv@^1.0.0" \
    --dependency "paho-mqtt@^1.6.1" \
    --dependency "django-crispy-forms@^2.0" \
    --dependency "crispy-bootstrap5@^0.7" \
    --dependency "django-debug-toolbar@^4.2.0" \
    --dependency "whitenoise@^6.5.0" \
    --dependency "psycopg2-binary" \
    --dev-dependency "black@^23.7.0" \
    --dev-dependency "isort@^5.12.0" \
    --dev-dependency "flake8@^6.1.0" \
    --no-interaction

# Creazione ambiente virtuale e installazione dipendenze
echo -e "${BLUE}Installazione dipendenze...${NC}"
poetry install

# Attivazione ambiente virtuale
poetry shell

# Creazione progetto Django
echo -e "${BLUE}Creazione progetto Django...${NC}"
django-admin startproject cercollettiva .

# Creazione app principali
echo -e "${BLUE}Creazione app Django...${NC}"
python manage.py startapp users
python manage.py startapp core
python manage.py startapp energy

# Creazione struttura directory
echo -e "${BLUE}Creazione struttura directory...${NC}"
mkdir -p templates/users templates/core templates/energy
mkdir -p static/{css,js,img}
mkdir -p media

# Creazione .env
echo -e "${BLUE}Creazione file .env...${NC}"
cat > .env << EOL
DEBUG=True
SECRET_KEY='django-insecure-generate-a-new-key-here'
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
EOL

# Configurazione settings.py
echo -e "${BLUE}Aggiornamento settings.py...${NC}"
cat > cercollettiva/settings.py << EOL
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'debug_toolbar',
    'users.apps.UsersConfig',
    'core.apps.CoreConfig',
    'energy.apps.EnergyConfig',
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
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'cercollettiva.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')

if DEBUG:
    INTERNAL_IPS = ['127.0.0.1']
EOL

# Esegui le migrazioni iniziali
echo -e "${BLUE}Esecuzione migrazioni...${NC}"
python manage.py migrate

# Creazione superuser
echo -e "${BLUE}Creazione superuser...${NC}"
python manage.py createsuperuser

echo -e "${GREEN}Setup completato con successo!${NC}"
echo -e "${BLUE}Per avviare il server di sviluppo:${NC}"
echo "python manage.py runserver"
