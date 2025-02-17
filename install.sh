#!/bin/bash

###########################################
#  CerCollettiva - Installation Script   #
#  Version: 1.0                          #
#  Author: Andrea Bernardi               #
#  Date: Febbraio 2025                   #
###########################################

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configurazione base
APP_NAME="CerCollettiva"
APP_ROOT="/home/pi"
APP_PATH="$APP_ROOT/$APP_NAME"
VENV_PATH="$APP_PATH/venv"
LOGS_PATH="$APP_PATH/logs"
PROJECT_PATH="$APP_PATH/app"

# Funzione di logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Verifica prerequisiti
check_prerequisites() {
    log "Verifica prerequisiti..."
    
    # Verifica utente non root
    if [ "$EUID" -eq 0 ]; then
        error "Non eseguire questo script come root"
    fi

    # Verifica presenza cartella app
    if [ ! -d "./app" ]; then
        error "Directory 'app' non trovata. Assicurati di essere nella directory corretta"
    fi

    # Verifica spazio disponibile
    local available_space=$(df -m "$APP_ROOT" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1000 ]; then
        error "Spazio su disco insufficiente (< 1GB)"
    fi

    # Verifica connessione internet
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        error "Connessione Internet non disponibile"
    fi
}

# Installazione dipendenze
install_dependencies() {
    log "Installazione dipendenze di sistema..."
    
    sudo apt update
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        python3-pip \
        python3-venv \
        nginx \
        postgresql \
        postgresql-contrib \
        supervisor \
        mosquitto \
        mosquitto-clients

    if [ $? -ne 0 ]; then
        error "Errore durante l'installazione delle dipendenze"
    fi
}

# Setup ambiente virtuale e dipendenze Python
setup_virtualenv() {
    log "Configurazione ambiente virtuale Python..."
    
    python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    
    pip install --upgrade pip wheel setuptools
    pip install -r "$PROJECT_PATH/requirements.txt"
    
    if [ $? -ne 0 ]; then
        error "Errore durante l'installazione delle dipendenze Python"
    fi
}

setup_database() {
    log "Configurazione PostgreSQL..."
    
    # Crea utente e database
    sudo -u postgres psql -c "CREATE USER cercollettiva WITH PASSWORD 'cercollettiva';"
    sudo -u postgres psql -c "CREATE DATABASE cercollettiva OWNER cercollettiva;"
    sudo -u postgres psql -c "ALTER USER cercollettiva CREATEDB;"
}

# Funzione per configurare le impostazioni Django
configure_django_settings() {
    log "Configurazione impostazioni Django..."
    
    local settings_dir="$PROJECT_PATH/cercollettiva/settings"
    local settings_file="$settings_dir/local.py"
    
    # Crea la directory settings se non esiste
    mkdir -p "$settings_dir"
    touch "$settings_dir/__init__.py"
    
    # Genera chiavi segrete
    local django_secret_key=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    local field_encryption_key=$(python -c '
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
')
    # Crea file settings/local.py
# Modifica la parte delle impostazioni Django in local.py
cat > "$settings_file" << EOL
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = '${django_secret_key}'
FIELD_ENCRYPTION_KEY = '${field_encryption_key}'
DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '$(hostname -I | cut -d' ' -f1)']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'encrypted_model_fields',
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'channels',
    'core',
    'energy',
    'users',
    'documents',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cercollettiva.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'cercollettiva.wsgi.application'
ASGI_APPLICATION = 'cercollettiva.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cercollettiva',
        'USER': 'cercollettiva',
        'PASSWORD': 'cercollettiva',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

AUTH_USER_MODEL = 'users.CustomUser'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
EOL



    # Aggiorna la configurazione MQTT se necessario
    local mqtt_file="$settings_dir/mqtt.py"
    cat > "$mqtt_file" << EOL
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_USERNAME = 'cercollettiva'
MQTT_PASSWORD = '$(openssl rand -base64 12)'
EOL

    chmod 600 "$settings_file"
    chmod 600 "$mqtt_file"
}

setup_django() {
    log "Configurazione Django..."
    
    # Configura le impostazioni
    configure_django_settings
    
    # Crea directory necessarie
    mkdir -p "$PROJECT_PATH/media"
    mkdir -p "$PROJECT_PATH/staticfiles"
    mkdir -p "$LOGS_PATH"
    
    # Inizializza database
    source "$VENV_PATH/bin/activate"
    cd "$PROJECT_PATH"
    
    # Assicurati che tutte le app abbiano le loro migrazioni
    python manage.py makemigrations users
    python manage.py makemigrations core
    python manage.py makemigrations energy
    python manage.py makemigrations documents
    
    # Applica le migrazioni nell'ordine corretto
    python manage.py migrate users
    python manage.py migrate auth
    python manage.py migrate admin
    python manage.py migrate contenttypes
    python manage.py migrate sessions
    python manage.py migrate core
    python manage.py migrate energy
    python manage.py migrate documents
    
    # Raccolta file statici
    python manage.py collectstatic --noinput
    
    # Crea superuser
    echo -e "\nCreazione account amministratore"
    python manage.py createsuperuser
}

# Configurazione Nginx
setup_nginx() {
    log "Configurazione Nginx..."
    
    sudo tee /etc/nginx/sites-available/cercollettiva > /dev/null << EOL
server {
    listen 80;
    server_name _;
    
    location /static/ {
        alias $PROJECT_PATH/staticfiles/;
    }

    location /media/ {
        alias $PROJECT_PATH/media/;
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOL

    sudo ln -sf /etc/nginx/sites-available/cercollettiva /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo systemctl restart nginx
}

# Configurazione Gunicorn
setup_gunicorn() {
    log "Configurazione Gunicorn..."
    
    sudo tee /etc/systemd/system/gunicorn.service > /dev/null << EOL
[Unit]
Description=CerCollettiva Gunicorn Daemon
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=$PROJECT_PATH
Environment="PATH=$VENV_PATH/bin"
Environment="DJANGO_SETTINGS_MODULE=cercollettiva.settings.local"
ExecStart=$VENV_PATH/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 cercollettiva.wsgi:application

[Install]
WantedBy=multi-user.target
EOL

    sudo systemctl daemon-reload
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
}

# Configurazione MQTT
setup_mqtt() {
    log "Configurazione MQTT..."
    
    # Estrai le credenziali MQTT dal file di configurazione
    local mqtt_user="cercollettiva"
    local mqtt_pass=$(openssl rand -base64 12)
    
    sudo mosquitto_passwd -c /etc/mosquitto/passwd "$mqtt_user" "$mqtt_pass"
    
    sudo tee /etc/mosquitto/conf.d/default.conf > /dev/null << EOL
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
EOL

    sudo systemctl restart mosquitto
}

# Configurazione Supervisor per processi MQTT
setup_supervisor() {
    log "Configurazione Supervisor..."
    
    sudo tee /etc/supervisor/conf.d/cercollettiva.conf > /dev/null << EOL
[program:cercollettiva_mqtt]
command=$VENV_PATH/bin/python $PROJECT_PATH/manage.py mqtt_client
directory=$PROJECT_PATH
user=pi
autostart=true
autorestart=true
stdout_logfile=$LOGS_PATH/mqtt.log
redirect_stderr=true
EOL

    sudo supervisorctl reread
    sudo supervisorctl update
}

# Funzione principale
main() {
    echo -e "${GREEN}=== Installazione CerCollettiva ===${NC}"
    
    check_prerequisites
    install_dependencies
    setup_virtualenv
    setup_database
    setup_django
    setup_nginx
    setup_gunicorn
    setup_mqtt
    setup_supervisor
    
    echo -e "\n${GREEN}=== Installazione completata! ===${NC}"
    echo -e "Accedi all'applicazione: http://$(hostname -I | cut -d' ' -f1)"
    echo -e "Pannello admin: http://$(hostname -I | cut -d' ' -f1)/admin"
}

# Avvio
main