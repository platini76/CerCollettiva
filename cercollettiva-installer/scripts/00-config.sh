#!/bin/bash

###########################################
#  CerCollettiva - Configuration File    #
#  Version: 1.0                          #
#  Author: Andrea Bernardi               #
#  Date: November 2024                   #
###########################################

# Previeni l'esecuzione diretta di questo script
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    echo "Questo script non dovrebbe essere eseguito direttamente"
    exit 1
fi

# Directory di base
export BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export APP_NAME="cercollettiva"
export APP_PATH="/home/pi/$APP_NAME"
export VENV_PATH="$APP_PATH/venv"
export BACKUP_PATH="$APP_PATH/backups"
export LOGS_PATH="$APP_PATH/logs"
export INSTALL_LOG="$APP_PATH/installation.log"

# Configurazione server
export NGINX_PORT=80
export GUNICORN_PORT=8000
export DOMAIN_NAME="localhost"
export ENABLE_SSL=false
export ENABLE_MONITORING=true

# Colori per output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export YELLOW='\033[1;33m'
export CYAN='\033[0;36m'
export NC='\033[0m'

# Configurazione task
declare -A TASKS=(
    ["prerequisites"]="Verifica prerequisiti"
    ["system_update"]="Aggiornamento sistema"
    ["dependencies"]="Installazione dipendenze"
    ["venv"]="Creazione ambiente virtuale"
    ["django"]="Setup Django"
    ["database"]="Configurazione database"
    ["static"]="Configurazione file statici"
    ["mqtt"]="Setup MQTT"
    ["nginx"]="Configurazione Nginx"
    ["gunicorn"]="Setup Gunicorn"
    ["monitoring"]="Setup monitoring"
    ["backup"]="Configurazione backup"
    ["superuser"]="Creazione superuser"
    ["finalization"]="Finalizzazione installazione"
)

# Dipendenze Python con versioni specifiche
declare -A PYTHON_PACKAGES=(
    ["django"]="5.0"
    ["python-dotenv"]="1.0.0"
    ["paho-mqtt"]="1.6.1"
    ["django-crispy-forms"]="2.1"
    ["crispy-bootstrap5"]="2023.10"
    ["whitenoise"]="6.6.0"
    ["channels"]="4.0.0"
    ["django-cors-headers"]="4.3.1"
    ["channels-redis"]="4.1.0"
    ["daphne"]="4.0.0"
    ["djangorestframework"]="3.14.0"
    ["django-widget-tweaks"]="1.5.0"
    ["django-debug-toolbar"]="4.2.0"
    ["gunicorn"]="21.2.0"
    ["django-filter"]="23.4"
    ["django-oauth-toolkit"]="2.3.0"
    ["drf-yasg"]="1.21.7"
    ["requests"]="2.31.0"
)

# Dipendenze di sistema
SYSTEM_PACKAGES=(
    "python3-pip"
    "python3-venv"
    "nginx"
    "git"
    "sqlite3"
    "supervisor"
    "build-essential"
    "python3-dev"
    "libffi-dev"
)

# Configurazioni hardware per diversi modelli Raspberry Pi
declare -A PI_CONFIGS=(
    ["Pi Zero"]="workers=1;threads=2;memory_limit=256"
    ["Pi 3"]="workers=2;threads=2;memory_limit=512"
    ["Pi 4"]="workers=3;threads=3;memory_limit=1024"
)

# Configurazione backup
BACKUP_RETENTION_DAYS=7
BACKUP_SCHEDULE="0 2 * * *"  # Ogni giorno alle 2 AM

# Configurazione monitoring
MONITORING_INTERVAL=5  # Minuti
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80
ALERT_THRESHOLD_DISK=80

# Configurazione logging
LOG_ROTATION_SIZE="10M"
LOG_RETENTION_COUNT=5

# Variabili di stato dell'installazione
export TOTAL_STEPS=${#TASKS[@]}
export CURRENT_STEP=0
declare -a COMPLETED_TASKS=()
export OPTIMIZE_FOR_LOW_MEMORY=false

# Funzione per caricare configurazioni locali se esistono
if [ -f "$BASE_DIR/local_config.sh" ]; then
    source "$BASE_DIR/local_config.sh"
fi

# Funzione per validare la configurazione
validate_config() {
    # Verifica directory di base
    if [ ! -d "$(dirname "$APP_PATH")" ]; then
        echo "Directory base non valida: $(dirname "$APP_PATH")"
        exit 1
    fi

    # Verifica porte
    if [ "$NGINX_PORT" -lt 1 ] || [ "$NGINX_PORT" -gt 65535 ]; then
        echo "Porta NGINX non valida: $NGINX_PORT"
        exit 1
    fi

    # Verifica altre configurazioni critiche
    if [ -z "$APP_NAME" ] || [ -z "$APP_PATH" ]; then
        echo "Configurazione incompleta: APP_NAME o APP_PATH mancanti"
        exit 1
    fi
}

# Esegui validazione configurazione
validate_config

# Esporta variabili per subprocess
export APP_NAME APP_PATH VENV_PATH BACKUP_PATH LOGS_PATH INSTALL_LOG