#!/bin/bash

###########################################
#  CerCollettiva - Installation Script   #
#  Version: 1.0                          #
#  Author: Andrea Bernardi               #
#  Date: November 2024                   #
###########################################

# Rileva il percorso dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_PATH="$SCRIPT_DIR/scripts"

# Verifica presenza cartella scripts
if [ ! -d "$SCRIPTS_PATH" ]; then
    echo "Errore: Directory scripts non trovata"
    exit 1
fi

# Verifica presenza dei file necessari
required_files=(
    "00-config.sh"
    "01-functions.sh"
    "02-system.sh"
    "03-app.sh"
    "04-services.sh"
    "05-finalize.sh"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$SCRIPTS_PATH/$file" ]; then
        echo "Errore: File $file non trovato in $SCRIPTS_PATH"
        exit 1
    fi
done

# Carica i file nell'ordine corretto
for file in "${required_files[@]}"; do
    source "$SCRIPTS_PATH/$file"
done

# Funzione principale
main() {
    # Verifica che non sia root
    if [ "$EUID" -eq 0 ]; then
        echo "Non eseguire questo script come root"
        exit 1
    fi

    # Verifica permessi directory
    if [ ! -w "$APP_ROOT" ]; then
        echo "Errore: Permessi insufficienti su $APP_ROOT"
        exit 1
    fi

    # Crea file di lock
    LOCK_FILE="/tmp/cercollettiva_install.lock"
    if [ -f "$LOCK_FILE" ]; then
        echo "Un'altra installazione è in corso. Se sei sicuro che non ci siano altre installazioni, rimuovi $LOCK_FILE"
        exit 1
    fi
    touch "$LOCK_FILE"

    # Inizializzazione
    show_banner
    
    # Backup di eventuali installazioni precedenti
    if [ -d "$APP_PATH" ]; then
        log "INFO" "Backup installazione precedente..."
        mv "$APP_PATH" "${APP_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    fi

    # Sequenza di installazione
    prepare_project_structure || handle_error "Errore durante la preparazione della struttura"
    install_system || handle_error "Errore durante l'installazione del sistema"
    setup_application || handle_error "Errore durante il setup dell'applicazione"
    configure_services || handle_error "Errore durante la configurazione dei servizi"
    finalize_installation || handle_error "Errore durante la finalizzazione"

    # Rimuovi file di lock alla fine
    rm -f "$LOCK_FILE"
}

# Gestione interruzioni
trap 'rm -f $LOCK_FILE; handle_error "Installazione interrotta dall'\''utente" 130' INT TERM

# Avvio
main "$@"
EOL