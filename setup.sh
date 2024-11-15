#!/bin/bash

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Banner ASCII
echo -e "${GREEN}"
cat << "EOF"
 =====================================================
   ______          ______    _ _     _   _   _           
  / ____/__  _____/ ____/___| | |___| |_| |_(_)_   ____ 
 / /   / _ \/ ___/ /   / __ \ | / _ \ __| __| \ \ / / _|
/ /___/  __/ /  / /___/ /_/ / |/  __/ |_| |_| |\ V / (_)
\____/\___/_/   \____/\____/|_|\___|\__|\__|_| \_/ \___/
                                                      
        Energy CAMMUNITY Management Platform
 =====================================================
         [ Developed by Andrea Bernardi ]
 =====================================================
EOF
echo -e "${NC}"

# Funzioni di utilità
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

print_step() {
    echo -e "\n${YELLOW}[STEP]${NC} $1..."
}

print_success() {
    echo -e "${GREEN}[✔] $1${NC}"
}

print_error() {
    echo -e "${RED}[✘] Error: $1${NC}"
}

check_error() {
    if [ $? -ne 0 ]; then
        print_error "$1"
        exit 1
    fi
}

# Lista delle dipendenze Python
PYTHON_PACKAGES=(
    "django"
    "python-dotenv"
    "paho-mqtt"
    "django-crispy-forms"
    "crispy-bootstrap5"
    "whitenoise"
    "channels"
    "django-cors-headers"
    "channels-redis"
    "daphne"
    "djangorestframework"
    "django-widget-tweaks"
    "django-debug-toolbar"
    "gunicorn"
    "django-filter"
    "django-oauth-toolkit"
    "drf-yasg"
    "requests"
)

# Progress bar
progress_bar() {
    local duration=$1
    local steps=20
    local step_duration=$(echo "scale=3; $duration/$steps" | bc)
    
    echo -ne "["
    for ((i=0; i<$steps; i++)); do
        echo -ne "${GREEN}#${NC}"
        sleep $step_duration
    done
    echo -ne "]\n"
}

# 1. Verifica prerequisiti
print_step "Verificando i prerequisiti"
if ! command -v python3 &> /dev/null; then
    print_error "Python3 non trovato"
    exit 1
fi
print_success "Prerequisiti verificati"

# 2. Aggiornamento sistema
print_step "Aggiornamento del sistema"
{
    sudo apt update
    sudo apt upgrade -y
} > /dev/null 2>&1 &
progress_bar 5
print_success "Sistema aggiornato"

# 3. Installazione dipendenze di sistema
print_step "Installazione dipendenze di sistema"
{
    sudo apt install -y python3-pip python3-venv nginx git
} > /dev/null 2>&1 &
progress_bar 3
print_success "Dipendenze di sistema installate"

# 4. Creazione ambiente virtuale
print_step "Creazione ambiente virtuale"
mkdir -p /home/pi/cercollettiva
cd /home/pi/cercollettiva
python3 -m venv venv
source venv/bin/activate
print_success "Ambiente virtuale creato"

# 5. Installazione dipendenze Python
print_step "Installazione dipendenze Python"
echo -e "\nInstallando i seguenti pacchetti:"
for package in "${PYTHON_PACKAGES[@]}"; do
    echo -ne "${BLUE}➜${NC} Installando $package..."
    pip install $package > /dev/null 2>&1
    check_error "Installazione di $package fallita"
    echo -e "${GREEN} ✔${NC}"
done
print_success "Dipendenze Python installate"

# 6. Configurazione .env
print_step "Configurazione file .env"
cat > .env << EOL
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | cut -d' ' -f1)
DATABASE_URL=sqlite:///db.sqlite3
EOL
print_success "File .env creato"

# 7. Configurazione Gunicorn
print_step "Configurazione Gunicorn"
sudo tee /etc/systemd/system/gunicorn.service << EOL > /dev/null
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=/home/pi/cercollettiva
Environment="PATH=/home/pi/cercollettiva/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=cercollettiva.settings.local"
ExecStart=/home/pi/cercollettiva/venv/bin/gunicorn \
          --workers 2 \
          --threads 2 \
          --bind 127.0.0.1:8000 \
          cercollettiva.wsgi:application \
          --log-level debug

[Install]
WantedBy=multi-user.target
EOL
print_success "Gunicorn configurato"

# 8. Configurazione Nginx
print_step "Configurazione Nginx"
sudo tee /etc/nginx/sites-available/cercollettiva << EOL > /dev/null
server {
    listen 80;
    server_name localhost;

    location /static/ {
        alias /home/pi/cercollettiva/staticfiles/;
        expires 30d;
        add_header Pragma public;
        add_header Cache-Control "public";
    }

    location /media/ {
        root /home/pi/cercollettiva;
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://127.0.0.1:8000;
    }
}
EOL
print_success "Nginx configurato"

# 9. Attivazione configurazione Nginx
print_step "Attivazione configurazione Nginx"
sudo ln -sf /etc/nginx/sites-available/cercollettiva /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
print_success "Configurazione Nginx attivata"

# 10. Configurazione permessi
print_step "Configurazione permessi"
sudo chown -R pi:www-data /home/pi/cercollettiva
sudo chmod -R 755 /home/pi/cercollettiva
print_success "Permessi configurati"

# 11. Migrazione database
print_step "Migrazione database"
python manage.py makemigrations --settings=cercollettiva.settings.local
python manage.py migrate --settings=cercollettiva.settings.local
check_error "Migrazione database fallita"
print_success "Database migrato"

# 12. Raccolta file statici
print_step "Raccolta file statici"
sudo rm -rf /home/pi/cercollettiva/staticfiles/*
python manage.py collectstatic --no-input --settings=cercollettiva.settings.local
sudo chown -R www-data:www-data /home/pi/cercollettiva/staticfiles
sudo chmod -R 755 /home/pi/cercollettiva/staticfiles
print_success "File statici raccolti"

# 13. Avvio servizi
print_step "Avvio servizi"
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl restart nginx
print_success "Servizi avviati"

# 14. Creazione superuser
print_step "Creazione superuser"
echo -e "\n${YELLOW}Per favore, crea un superuser per l'amministrazione:${NC}"
python manage.py createsuperuser --settings=cercollettiva.settings.local

# Output finale
echo -e "\n${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}             Installazione completata con successo!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "\n${BLUE}Accedi all'applicazione:${NC}"
echo -e "➜ Frontend: http://$(hostname -I | cut -d' ' -f1)"
echo -e "➜ Admin: http://$(hostname -I | cut -d' ' -f1)/admin"
echo -e "\n${YELLOW}Stato dei servizi:${NC}"
echo -e "════════════════════════════════════════════════"
sudo systemctl status nginx | grep Active
sudo systemctl status gunicorn | grep Active
echo -e "════════════════════════════════════════════════\n"
