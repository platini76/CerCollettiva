#!/bin/bash

###########################################
#  CerCollettiva - System Installation   #
#  Version: 1.0                          #
#  Author: Andrea Bernardi               #
#  Date: November 2024                   #
###########################################

# Previeni l'esecuzione diretta di questo script
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    echo "Questo script non dovrebbe essere eseguito direttamente"
    exit 1
fi

# Rileva modello Raspberry Pi
detect_raspberry_model() {
    local model=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown")
    log "INFO" "Rilevato modello Raspberry Pi: $model"
    
    case "$model" in
        *"Zero"*)
            PI_MODEL="Pi Zero"
            OPTIMIZE_FOR_LOW_MEMORY=true
            ;;
        *"Pi 3"*)
            PI_MODEL="Pi 3"
            ;;
        *"Pi 4"*)
            PI_MODEL="Pi 4"
            ;;
        *)
            PI_MODEL="Unknown"
            log "WARNING" "Modello Raspberry Pi non riconosciuto"
            ;;
    esac
    
    # Applica configurazioni specifiche per il modello
    if [ ! -z "${PI_CONFIGS[$PI_MODEL]}" ]; then
        IFS=';' read -r -a configs <<< "${PI_CONFIGS[$PI_MODEL]}"
        for config in "${configs[@]}"; do
            export "$config"
        done
    fi
}

# Aggiornamento del sistema
update_system() {
    log "INFO" "Avvio aggiornamento del sistema..."
    update_progress "system_update" "in_progress"
    
    # Backup sources.list
    cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null
    
    {
        # Aggiornamento repository
        log "INFO" "Aggiornamento repository..."
        sudo apt update
        
        # Aggiornamento pacchetti
        log "INFO" "Aggiornamento pacchetti..."
        sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y
        
        # Pulizia
        log "INFO" "Pulizia pacchetti non necessari..."
        sudo apt autoremove -y
        sudo apt clean
    } >> "$INSTALL_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "Sistema aggiornato con successo"
        update_progress "system_update" "completed"
    else
        # Ripristino backup sources.list in caso di errore
        sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list 2>/dev/null
        handle_error "Errore durante l'aggiornamento del sistema"
    fi
}

# Installazione dipendenze di sistema
install_system_dependencies() {
    log "INFO" "Installazione dipendenze di sistema..."
    update_progress "dependencies" "in_progress"
    
    local total_packages=${#SYSTEM_PACKAGES[@]}
    local current_package=0
    
    # Creazione file di lock
    touch "$APP_PATH/.installing_dependencies"
    
    for package in "${SYSTEM_PACKAGES[@]}"; do
        current_package=$((current_package + 1))
        log "INFO" "Installazione $package ($current_package/$total_packages)"
        
        {
            sudo DEBIAN_FRONTEND=noninteractive apt install -y "$package"
        } >> "$INSTALL_LOG" 2>&1
        
        if [ $? -ne 0 ]; then
            rm -f "$APP_PATH/.installing_dependencies"
            handle_error "Errore durante l'installazione di $package"
        fi
        
        # Aggiorna la progress bar
        local sub_progress=$((current_package * 100 / total_packages))
        echo $sub_progress > "$APP_PATH/.install_progress"
    done
    
    # Rimuovi file di lock e progress
    rm -f "$APP_PATH/.installing_dependencies"
    rm -f "$APP_PATH/.install_progress"
    
    log "SUCCESS" "Dipendenze di sistema installate con successo"
    update_progress "dependencies" "completed"
}

# Setup ambiente virtuale Python
setup_virtualenv() {
    log "INFO" "Configurazione ambiente virtuale Python..."
    update_progress "venv" "in_progress"
    
    if [ -d "$VENV_PATH" ]; then
        log "WARNING" "Ambiente virtuale esistente trovato, creazione backup..."
        mv "$VENV_PATH" "${VENV_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    {
        python3 -m venv "$VENV_PATH"
        source "$VENV_PATH/bin/activate"
        pip install --upgrade pip wheel setuptools
    } >> "$INSTALL_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "Ambiente virtuale creato con successo"
        update_progress "venv" "completed"
    else
        handle_error "Errore durante la creazione dell'ambiente virtuale"
    fi
}

# Installazione dipendenze Python
install_python_dependencies() {
    log "INFO" "Installazione dipendenze Python..."
    source "$VENV_PATH/bin/activate"
    
    local total_packages=${#PYTHON_PACKAGES[@]}
    local current_package=0
    
    for package in "${!PYTHON_PACKAGES[@]}"; do
        current_package=$((current_package + 1))
        version=${PYTHON_PACKAGES[$package]}
        log "INFO" "Installazione $package==$version ($current_package/$total_packages)"
        
        {
            pip install "$package==$version"
        } >> "$INSTALL_LOG" 2>&1
        
        if [ $? -ne 0 ]; then
            log "WARNING" "Primo tentativo fallito per $package, ritento..."
            pip install --no-cache-dir "$package==$version" >> "$INSTALL_LOG" 2>&1
            
            if [ $? -ne 0 ]; then
                handle_error "Errore durante l'installazione di $package"
            fi
        fi
        
        # Verifica installazione
        if ! pip show "$package" > /dev/null 2>&1; then
            handle_error "Pacchetto $package non installato correttamente"
        fi
    done
    
    log "SUCCESS" "Dipendenze Python installate correttamente"
}

# Ottimizzazioni di sistema
optimize_system() {
    log "INFO" "Applicazione ottimizzazioni di sistema..."
    
    # Ottimizzazioni per memoria limitata
    if [ "$OPTIMIZE_FOR_LOW_MEMORY" = true ]; then
        log "INFO" "Applicando ottimizzazioni per memoria limitata..."
        
        # Configurazione swap
        if [ ! -f /swapfile ]; then
            sudo fallocate -l 1G /swapfile
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi
        
        # Ottimizzazioni kernel
        echo "vm.swappiness=60" | sudo tee /etc/sysctl.d/99-swappiness.conf
        echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.d/99-swappiness.conf
        sudo sysctl -p /etc/sysctl.d/99-swappiness.conf
    fi
    
    log "SUCCESS" "Ottimizzazioni di sistema applicate"
}

# Funzione principale di installazione sistema
install_system() {
    log "INFO" "Avvio installazione componenti di sistema..."
    
    # Controlli preliminari
    check_internet
    detect_raspberry_model
    
    # Sequenza di installazione
    create_backup
    update_system
    install_system_dependencies
    setup_virtualenv
    install_python_dependencies
    optimize_system
    
    log "SUCCESS" "Installazione componenti di sistema completata"
}