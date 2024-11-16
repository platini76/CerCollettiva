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
    use epoll;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Dimensione del buffer
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;

    # Gzip
    gzip on;
    gzip_disable "msie6";
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # File MIME
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log combined buffer=512k flush=1m;
    error_log /var/log/nginx/error.log warn;

    # Inclusione configurazioni aggiuntive
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOL

    # Configurazione del sito
    sudo tee /etc/nginx/sites-available/cercollettiva > /dev/null << EOL
server {
    listen 80;
    server_name _;
    charset utf-8;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data:; font-src 'self' data:;" always;
    
    # File statici
    location /static/ {
        alias $STATIC_PATH/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
        
        # Ottimizzazione performance
        tcp_nodelay off;
        open_file_cache max=3000 inactive=120s;
        open_file_cache_valid 45s;
        open_file_cache_min_uses 2;
        open_file_cache_errors off;
    }

    # Media files
    location /media/ {
        alias $MEDIA_PATH/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Proxy verso Gunicorn
    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_redirect off;
        proxy_read_timeout 90;
        proxy_connect_timeout 90;
        proxy_send_timeout 90;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
    }
    
    # Custom error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    
    # Deny access to .git and other hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
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
WorkingDirectory=$PROJECT_PATH
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
    --capture-output \
    --enable-stdio-inheritance \
    cercollettiva.wsgi:application

# Riavvio automatico
Restart=always
RestartSec=5

# Limiti di sistema
LimitNOFILE=65535
TimeoutStartSec=10
TimeoutStopSec=10

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
command=$VENV_PATH/bin/python $PROJECT_PATH/manage.py mqtt_client
directory=$PROJECT_PATH
user=pi
numprocs=1
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
redirect_stderr=true
stdout_logfile=$LOGS_PATH/mqtt.log
stderr_logfile=$LOGS_PATH/mqtt.error.log
priority=10

[program:cercollettiva_worker]
command=$VENV_PATH/bin/python $PROJECT_PATH/manage.py process_tasks
directory=$PROJECT_PATH
user=pi
numprocs=1
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
redirect_stderr=true
stdout_logfile=$LOGS_PATH/worker.log
stderr_logfile=$LOGS_PATH/worker.error.log
priority=20

[group:cercollettiva]
programs=cercollettiva_mqtt,cercollettiva_worker
priority=999
EOL

    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start all
    
    log "SUCCESS" "Supervisor configurato con successo"
}

# Setup servizi di monitoraggio
setup_monitoring() {
    log "INFO" "Configurazione monitoraggio..."
    update_progress "monitoring" "in_progress"
    
    # Script di monitoraggio
    cat > "$PROJECT_PATH/monitor.sh" << 'EOL'
#!/bin/bash
LOGS_PATH="$1/logs"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80
ALERT_THRESHOLD_DISK=90

while true; do
    # Monitora risorse
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    DISK_USAGE=$(df -h / | awk 'NR==2 {print int($5)}')
    TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d. -f1)
    
    # Log delle metriche
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] CPU: ${CPU_USAGE}% | RAM: ${MEM_USAGE}% | Disk: ${DISK_USAGE}% | Temp: ${TEMP}°C" >> "$LOGS_PATH/system.log"
    
    # Controllo soglie
    if [ "$CPU_USAGE" -gt "$ALERT_THRESHOLD_CPU" ]; then
        echo "[$timestamp] ALERT: CPU usage high (${CPU_USAGE}%)" >> "$LOGS_PATH/alerts.log"
    fi
    
    if [ "$MEM_USAGE" -gt "$ALERT_THRESHOLD_MEM" ]; then
        echo "[$timestamp] ALERT: Memory usage high (${MEM_USAGE}%)" >> "$LOGS_PATH/alerts.log"
    fi
    
    if [ "$DISK_USAGE" -gt "$ALERT_THRESHOLD_DISK" ]; then
        echo "[$timestamp] ALERT: Disk usage high (${DISK_USAGE}%)" >> "$LOGS_PATH/alerts.log"
    fi
    
    # Controllo servizi
    for service in nginx gunicorn supervisor; do
        if ! systemctl is-active --quiet $service; then
            echo "[$timestamp] WARNING: $service non attivo" >> "$LOGS_PATH/alerts.log"
            sudo systemctl restart $service
        fi
    done
    
    # Rotazione log se necessario
    for logfile in "$LOGS_PATH"/*.log; do
        if [ -f "$logfile" ] && [ $(stat -f%z "$logfile") -gt 10485760 ]; then  # 10MB
            mv "$logfile" "${logfile}.1"
        fi
    done
    
    sleep 300  # Controllo ogni 5 minuti
done
EOL

    chmod +x "$PROJECT_PATH/monitor.sh"
    
    # Servizio systemd per il monitoraggio
    sudo tee /etc/systemd/system/cercollettiva-monitor.service > /dev/null << EOL
[Unit]
Description=CerCollettiva System Monitor
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/bin/bash $PROJECT_PATH/monitor.sh $PROJECT_PATH
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
