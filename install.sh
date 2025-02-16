#!/bin/bash

###########################################
#  CerCollettiva - Installation Script   #
#  Version: 2.0                          #
#  Author: Andrea Bernardi               #
#  Date: Febbraio 2025                   #
###########################################

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configurazione base
APP_NAME="cercollettiva"
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
        sqlite3 \
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

# Configurazione Django
setup_django() {
    log "Configurazione Django..."
    
    source "$VENV_PATH/bin/activate"
    cd "$PROJECT_PATH"
    
    # Crea file .env
    cat > .env << EOL
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | cut -d' ' -f1)
DATABASE_URL=sqlite:///db.sqlite3
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=cercollettiva
MQTT_PASSWORD=$(openssl rand -base64 12)
TIME_ZONE=Europe/Rome
LANGUAGE_CODE=it
EOL

    # Setup database e file statici
    python manage.py migrate
    python manage.py collectstatic --noinput
    
    # Crea superuser
    echo -e "\n${YELLOW}Creazione account amministratore${NC}"
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
    
    MQTT_USER=$(grep MQTT_USERNAME .env | cut -d= -f2)
    MQTT_PASS=$(grep MQTT_PASSWORD .env | cut -d= -f2)
    
    sudo mosquitto_passwd -c /etc/mosquitto/passwd "$MQTT_USER" "$MQTT_PASS"
    
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