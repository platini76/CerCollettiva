// static/js/mqtt-status.js
class MQTTStatusManager {
    constructor() {
        this.statusMap = {
            'connected': {
                text: 'Connesso al Broker MQTT',
                class: 'connected'
            },
            'connecting': {
                text: 'Connessione in corso...',
                class: 'connecting'
            },
            'disconnected': {
                text: 'Disconnesso',
                class: 'disconnected'
            },
            'error': {
                text: 'Errore di connessione',
                class: 'error'
            }
        };

        this.updateInterval = null;
        this.initialize();
    }

    initialize() {
        this.updateStatus();
        this.startUpdateInterval();
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
    }

    formatNumber(num) {
        return new Intl.NumberFormat('it-IT').format(num);
    }

    updateLastUpdate() {
        const now = new Date();
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = `Ultimo aggiornamento: ${now.toLocaleTimeString()}`;
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/energy/api/mqtt/status/');
            if (!response.ok) {
                throw new Error(`Errore nella richiesta: ${response.status}`);
            }
            const data = await response.json();
            this.updateUI(data);
            this.updateLastUpdate();
        } catch (error) {
            console.error('Errore nel recupero dello stato MQTT:', error);
            this.showError(error);
        }
    }

    updateUI(data) {
        const statusInfo = this.statusMap[data.connection] || this.statusMap['disconnected'];
        
        // Aggiorna stato connessione
        const statusIndicator = document.getElementById('connectionStatus');
        const connectionText = document.getElementById('connectionText');
        if (statusIndicator && connectionText) {
            statusIndicator.className = 'status-indicator ' + statusInfo.class;
            connectionText.textContent = statusInfo.text;
        }

        // Aggiorna contatori e metriche
        this.updateElement('mqtt-connection-status', data.connection);
        this.updateElement('mqtt-messages-processed', this.formatNumber(data.messages_processed));
        this.updateElement('mqtt-connected-devices', this.formatNumber(data.connected_devices));
        
        // Aggiorna errore se presente
        if (data.last_error) {
            this.updateElement('mqtt-last-error', data.last_error);
        }
        
        // Aggiorna metriche di performance
        if (data.performance) {
            this.updateElement('mqtt-message-rate', 
                data.performance.message_rate.toFixed(2));
            this.updateElement('mqtt-processing-time', 
                data.performance.average_processing_time.toFixed(2));
        }
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    showError(error) {
        const statusIndicator = document.getElementById('connectionStatus');
        const connectionText = document.getElementById('connectionText');
        
        if (statusIndicator && connectionText) {
            statusIndicator.className = 'status-indicator error';
            connectionText.textContent = 'Errore di comunicazione';
            connectionText.classList.add('text-danger');
        }

        this.updateElement('mqtt-connection-status', 'Error');
        this.updateElement('mqtt-last-error', error.message);
    }

    startUpdateInterval() {
        if (!this.updateInterval) {
            this.updateInterval = setInterval(() => this.updateStatus(), 5000);
        }
    }

    stopUpdateInterval() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            this.stopUpdateInterval();
        } else {
            this.updateStatus();
            this.startUpdateInterval();
        }
    }
}

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.mqttStatus = new MQTTStatusManager();
});
