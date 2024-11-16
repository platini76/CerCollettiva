#!/bin/bash

###########################################
#  CerCollettiva - Services Setup        #
#  Version: 1.0                          #
#  Author: Andrea Bernardi               #
#  Date: November 2024                   #
###########################################

# Previeni l'esecuzione diretta di questo script
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    echo "Questo script non dovrebbe essere eseguito direttamente"
    exit 1
fi

# Configurazione Nginx
setup_nginx() {
    log "INFO" "Configurazione Nginx..."
    update_progress "nginx" "in_progress"
    
    # Backup configurazione esistente
    if [ -f /etc/nginx/sites-enabled/default ]; then
        sudo mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup
    fi
    
    # Configurazione ottimizzata per Raspberry Pi
    local worker_processes=1
    if [[ "$PI_MODEL" == "Pi 4" ]]; then
        worker_processes=2
    fi
    
    # Configurazione principale Nginx
    sudo tee /etc/nginx/nginx.conf > /dev/null << EOL
user www-data;
worker_processes $worker_processes;
pid /run/nginx.pid;

events {
    worker_connections 512;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;
    gzip_disable "msie6";
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOL

    # Configurazione del sito
    sudo tee /etc/nginx/sites-available/cercollettiva > /dev/null << EOL
server {
    listen 80;
    server_name _;
    client_max_body_size 10M;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    location /static/ {
        alias $APP_PATH/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    location /media/ {
        alias $APP_PATH/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 90;
        proxy_redirect off;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Custom error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
EOL

    # Attiva il sito
    sudo ln -sf /etc/nginx/sites-available/cercollettiva /etc/nginx/sites-enabled/
    
    # Test configurazione
    sudo nginx -t >> "$INSTALL_LOG" 2>&1
    if [ $? -ne 0 ]; then
        # Ripristina backup in caso di errore
        sudo mv /etc/nginx/sites-enabled/default.backup /etc/nginx/sites-enabled/default 2>/dev/null
        handle_error "Configurazione Nginx non valida"
    fi
    
    # Riavvia Nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    log "SUCCESS" "Nginx configurato con successo"
    update_progress "nginx" "completed"
}

# Configurazione Gunicorn
setup_gunicorn() {
    log "INFO" "Configurazione Gunicorn..."
    update_progress "gunicorn" "in_progress"
    
    # Determina numero di workers in base al modello
    local workers=1
    local threads=2
    if [[ "$PI_MODEL" == "Pi 4" ]]; then
        workers=2
        threads=4
    fi

    # Configurazione systemd
    sudo tee /etc/systemd/system/gunicorn.service > /dev/null << EOL
[Unit]
Description=CerCollettiva Gunicorn Daemon
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=$APP_PATH
Environment="PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DJANGO_SETTINGS_MODULE=cercollettiva.settings.local"
ExecStart=$VENV_PATH/bin/gunicorn \
    --workers $workers \
    --threads $threads \
    --worker-class=gthread \
    --worker-tmp-dir=/dev/shm \
    --bind 127.0.0.1:8000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keepalive 2 \
    --log-level=info \
    --access-logfile=$LOGS_PATH/gunicorn-access.log \
    --error-logfile=$LOGS_PATH/gunicorn-error.log \
    cercollettiva.wsgi:application

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

    # Ricarica systemd e avvia Gunicorn
    sudo systemctl daemon-reload
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
    
    # Verifica stato
    if ! sudo systemctl is-active --quiet gunicorn; then
        handle_error "Gunicorn non si è avviato correttamente"
    fi
    
    log "SUCCESS" "Gunicorn configurato con successo"
    update_progress "gunicorn" "completed"
}

# Setup Supervisor (per processi MQTT e worker)
setup_supervisor() {
    log "INFO" "Configurazione Supervisor..."
    
    sudo tee /etc/supervisor/conf.d/cercollettiva.conf > /dev/null << EOL
[program:cercollettiva_mqtt]
command=$VENV_PATH/bin/python $APP_PATH/manage.py mqtt_client
directory=$APP_PATH
user=pi
numprocs=1
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$LOGS_PATH/mqtt.log
priority=10

[program:cercollettiva_worker]
command=$VENV_PATH/bin/python $APP_PATH/manage.py process_tasks
directory=$APP_PATH
user=pi
numprocs=1
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$LOGS_PATH/worker.log
priority=20
EOL

    sudo supervisorctl reread
    sudo supervisorctl update
    
    log "SUCCESS" "Supervisor configurato con successo"
}

# Setup servizi di monitoraggio
setup_monitoring() {
    log "INFO" "Configurazione monitoraggio..."
    update_progress "monitoring" "in_progress"
    
    # Script di monitoraggio
    cat > "$APP_PATH/monitor.sh" << 'EOL'
#!/bin/bash
LOGS_PATH="$1/logs"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80

while true; do
    # Monitora CPU, RAM e temperatura
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d. -f1)
    
    # Log delle metriche
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] CPU: ${CPU_USAGE}% | RAM: ${MEM_USAGE}% | Temp: ${TEMP}°C" >> "$LOGS_PATH/system.log"
    
    # Controllo servizi
    for service in nginx gunicorn supervisor; do
        if ! systemctl is-active --quiet $service; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $service non attivo" >> "$LOGS_PATH/system.log"
            sudo systemctl restart $service
        fi
    done
    
    # Rotazione log se necessario
    if [ $(stat -f%z "$LOGS_PATH/system.log") -gt 10485760 ]; then  # 10MB
        mv "$LOGS_PATH/system.log" "$LOGS_PATH/system.log.1"
    fi
    
    sleep 300  # Controllo ogni 5 minuti
done
EOL

    chmod +x "$APP_PATH/monitor.sh"
    
    # Servizio systemd per il monitoraggio
    sudo tee /etc/systemd/system/cercollettiva-monitor.service > /dev/null << EOL
[Unit]
Description=CerCollettiva System Monitor
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/bin/bash $APP_PATH/monitor.sh $APP_PATH
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

    sudo systemctl daemon-reload
    sudo systemctl start cercollettiva-monitor
    sudo systemctl enable cercollettiva-monitor
    
    log "SUCCESS" "Monitoraggio configurato con successo"
    update_progress "monitoring" "completed"
}

# Funzione principale setup servizi
configure_services() {
    log "INFO" "Avvio configurazione servizi..."
    
    setup_nginx
    setup_gunicorn
    setup_supervisor
    setup_monitoring
    
    log "SUCCESS" "Configurazione servizi completata"
}