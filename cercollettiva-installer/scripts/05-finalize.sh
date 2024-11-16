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
    if [ ! -w "$APP_PATH/media" ] || [ ! -w "$APP_PATH/staticfiles" ]; then
        log "ERROR" "Permessi directory non corretti"
        errors=$((errors + 1))
    fi
    
    # Test connessione MQTT
    timeout 5 mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t "test" &>/dev/null
    if [ $? -ne 0 ]; then
        log "WARNING" "Test connessione MQTT fallito"
        errors=$((errors + 1))
    fi
    
    return $errors
}

# Generazione report finale
generate_report() {
    local report_file="$APP_PATH/installation_report.txt"
    
    {
        echo "=== CerCollettiva Installation Report ==="
        echo "Data: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Modello Raspberry Pi: $PI_MODEL"
        echo ""
        
        echo "== Versioni Software =="
        echo "Python: $(python3 --version)"
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
        
        echo "== Note Importanti =="
        echo "1. Backup giornalieri in: $BACKUP_PATH"
        echo "2. Log di sistema in: $LOGS_PATH"
        echo "3. File configurazione in: $APP_PATH/.env"
        
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
    
    # Ottimizza database
    source "$VENV_PATH/bin/activate"
    python manage.py clearsessions
    
    # Pulizia cache pip
    pip cache purge
    
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
    echo -e "${GREEN}║${NC}  Documentazione: $APP_PATH/installation_report.txt      ${GREEN}║${NC}"
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