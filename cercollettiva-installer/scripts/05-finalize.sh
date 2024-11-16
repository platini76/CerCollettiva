#!/bin/bash

###########################################
#  CerCollettiva - Finalization         #
#  Version: 1.0                         #
#  Author: Andrea Bernardi              #
#  Date: November 2024                  #
###########################################

# Previeni l'esecuzione diretta di questo script
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    echo "Questo script non dovrebbe essere eseguito direttamente"
    exit 1
fi

# Creazione superuser
create_superuser() {
    log "INFO" "Creazione superuser Django..."
    update_progress "superuser" "in_progress"
    
    cd "$PROJECT_PATH"
    source "$VENV_PATH/bin/activate"
    
    echo -e "\n${YELLOW}Creazione account amministratore${NC}"
    echo -e "${BLUE}Per favore, inserisci le credenziali per l'account amministratore:${NC}\n"
    
    python manage.py createsuperuser
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "Superuser creato con successo"
        update_progress "superuser" "completed"
    else
        handle_error "Errore durante la creazione del superuser"
    fi
}

# Test finale dell'installazione
test_installation() {
    log "INFO" "Esecuzione test finali..."
    
    local errors=0
    
    # Test connessione Django
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"
    if [ $? -ne 0 ]; then
        log "ERROR" "Test connessione Django fallito"
        errors=$((errors + 1))
    fi
    
    # Test stato servizi
    for service in nginx gunicorn supervisor cercollettiva-monitor; do
        if ! sudo systemctl is-active --quiet $service; then
            log "ERROR" "Servizio $service non attivo"
            errors=$((errors + 1))
        fi
    done
    
    # Test permessi directory
    if [ ! -w "$MEDIA_PATH" ] || [ ! -w "$STATIC_PATH" ]; then
        log "ERROR" "Permessi directory non corretti"
        errors=$((errors + 1))
    fi
    
    # Test connessione MQTT
    timeout 5 mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "test" &>/dev/null
    if [ $? -ne 0 ]; then
        log "WARNING" "Test connessione MQTT fallito"
        errors=$((errors + 1))
    fi
    
    # Test database
    cd "$PROJECT_PATH"
    source "$VENV_PATH/bin/activate"
    python manage.py check --database default
    if [ $? -ne 0 ]; then
        log "ERROR" "Test database fallito"
        errors=$((errors + 1))
    fi
    
    return $errors
}

# Generazione report finale
generate_report() {
    local report_file="$PROJECT_PATH/installation_report.txt"
    
    {
        echo "=== CerCollettiva Installation Report ==="
        echo "Data: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Modello Raspberry Pi: $PI_MODEL"
        echo ""
        
        echo "== Versioni Software =="
        echo "Python: $(python3 --version)"
        echo "Django: $(python -c 'import django; print(django.get_version())')"
        echo "Nginx: $(nginx -v 2>&1)"
        echo "Database: SQLite $(sqlite3 --version)"
        echo ""
        
        echo "== Stato Servizi =="
        for service in nginx gunicorn supervisor cercollettiva-monitor; do
            echo "$service: $(systemctl is-active $service)"
        done
        echo ""
        
        echo "== Informazioni Sistema =="
        echo "CPU: $(vcgencmd measure_clock arm | cut -d= -f2)"
        echo "Temperatura: $(vcgencmd measure_temp)"
        echo "Memoria: $(free -h | grep Mem)"
        echo "Spazio Disco: $(df -h /)"
        echo ""
        
        echo "== URL Accesso =="
        echo "Frontend: http://$(hostname -I | cut -d' ' -f1)"
        echo "Admin: http://$(hostname -I | cut -d' ' -f1)/admin"
        echo ""
        
        echo "== Percorsi Importanti =="
        echo "1. Applicazione: $PROJECT_PATH"
        echo "2. File statici: $STATIC_PATH"
        echo "3. File media: $MEDIA_PATH"
        echo "4. Log di sistema: $LOGS_PATH"
        echo "5. Backup: $BACKUP_PATH"
        echo "6. Ambiente virtuale: $VENV_PATH"
        echo ""
        
        echo "== Note Importanti =="
        echo "1. Backup giornalieri automatici alle 2:00 AM"
        echo "2. Monitoraggio sistema attivo (check ogni 5 minuti)"
        echo "3. Log rotation configurato"
        echo "4. Ottimizzazioni applicate per $PI_MODEL"
        
    } > "$report_file"
    
    log "SUCCESS" "Report generato: $report_file"
}

# Pulizia post-installazione
cleanup_installation() {
    log "INFO" "Pulizia post-installazione..."
    
    # Rimuovi file temporanei
    rm -f "$APP_PATH/.install_progress"
    rm -f "$APP_PATH/.install_error"
    rm -f "$APP_PATH/.install.pid"
    rm -f "/tmp/cercollettiva_install.lock"
    
    # Ottimizza database
    cd "$PROJECT_PATH"
    source "$VENV_PATH/bin/activate"
    python manage.py clearsessions
    
    # Pulizia cache
    pip cache purge
    sudo apt clean
    
    # Mantieni solo gli ultimi 5 backup
    cd "$BACKUP_PATH"
    ls -t | tail -n +6 | xargs -r rm
    
    log "SUCCESS" "Pulizia completata"
}

# Mostra istruzioni finali
show_final_instructions() {
    echo -e "\n${GREEN}╔════════════════ Installazione Completata ════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║${NC}  CerCollettiva è stato installato con successo!        ${GREEN}║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║${NC}  Accedi all'applicazione:                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Frontend: http://$(hostname -I | cut -d' ' -f1)                ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Admin: http://$(hostname -I | cut -d' ' -f1)/admin            ${GREEN}║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║${NC}  Documentazione: $PROJECT_PATH/installation_report.txt      ${GREEN}║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║${NC}  Per assistenza: github.com/andreabernardi/cercollettiva${GREEN}║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}\n"
}

# Funzione principale di finalizzazione
finalize_installation() {
    log "INFO" "Avvio finalizzazione installazione..."
    
    create_superuser
    
    local test_errors=$(test_installation)
    if [ $test_errors -gt 0 ]; then
        log "WARNING" "Installazione completata con $test_errors warning/errori"
    else
        log "SUCCESS" "Test installazione completati con successo"
    fi
    
    generate_report
    cleanup_installation
    show_final_instructions
    
    log "SUCCESS" "Installazione CerCollettiva completata!"
    update_progress "finalization" "completed"
}
