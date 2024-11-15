#!/bin/bash

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Controlla se il comando precedente ha avuto successo
check_error() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}Errore durante l'esecuzione dello script. Uscita.${NC}"
        exit 1
    fi
}

# Verifica i privilegi di amministratore
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Esegui lo script come root o con sudo.${NC}"
    exit 1
fi

echo -e "${BLUE}Setup ambiente di sviluppo CerCollettiva${NC}"
echo "----------------------------------------"

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 non trovato. Installazione...${NC}"
    sudo apt update && sudo apt install -y python3 python3-pip
    check_error
else
    echo -e "${GREEN}Python3 trovato.${NC}"
fi

# Verifica Poetry
if ! command -v poetry &> /dev/null; then
    echo -e "${BLUE}Installazione Poetry...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    check_error
    export PATH="$HOME/.local/bin:$PATH"
else
    echo -e "${GREEN}Poetry già installato.${NC}"
fi

# Creazione directory progetto
PROJECT_DIR="cercollettiva"
echo -e "${BLUE}Creazione directory progetto...${NC}"
mkdir -p "$PROJECT_DIR"
check_error
cd "$PROJECT_DIR"

# Inizializzazione Poetry
echo -e "${BLUE}Inizializzazione Poetry...${NC}"
poetry init --name "cercollettiva" \
    --description "Software opensource per la gestione delle comunità energetiche" \
    --author "Andrea Bernardi<bernardi.andrea@gmail.com>" \
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
check_error

# Installazione dipendenze
echo -e "${BLUE}Installazione dipendenze...${NC}"
poetry install
check_error

# Attivazione ambiente virtuale
poetry shell

# Creazione progetto Django
echo -e "${BLUE}Creazione progetto Django...${NC}"
django-admin startproject cercollettiva .
check_error

# Creazione app principali
for app in users core energy; do
    echo -e "${BLUE}Creazione app Django: $app...${NC}"
    python manage.py startapp "$app"
    check_error
done

# Creazione struttura directory
echo -e "${BLUE}Creazione struttura directory...${NC}"
mkdir -p templates/{users,core,energy}
mkdir -p static/{css,js,img}
mkdir -p media
check_error

# Creazione file .env
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

# Configurazione iniziale database
echo -e "${BLUE}Esecuzione migrazioni...${NC}"
python manage.py migrate
check_error

# Creazione superuser
echo -e "${BLUE}Creazione superuser Django...${NC}"
python manage.py createsuperuser --email "admin@example.com"
check_error

echo -e "${GREEN}Setup completato con successo!${NC}"
echo -e "${BLUE}Per avviare il server di sviluppo:${NC}"
echo "python manage.py runserver"
