#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Carica i vari script
source "$SCRIPT_DIR/scripts/00-config.sh"
source "$SCRIPT_DIR/scripts/01-functions.sh"
source "$SCRIPT_DIR/scripts/02-system.sh"
source "$SCRIPT_DIR/scripts/03-app.sh"
source "$SCRIPT_DIR/scripts/04-services.sh"
source "$SCRIPT_DIR/scripts/05-finalize.sh"

# Main execution
show_banner
check_prerequisites

# Installation sequence
install_system
setup_application
configure_services
finalize_installation