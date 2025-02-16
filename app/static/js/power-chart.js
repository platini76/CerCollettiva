// static/js/power-chart.js
class PowerChartManager {
    constructor(plantId) {
        this.plantId = plantId;
        this.chart = null;
        this.currentHours = 24;
        this.updateInterval = null;
        
        this.initialize();
    }

    initialize() {
        this.setupChart();
        this.setupEventListeners();
        this.startUpdateInterval();
        
        // Gestione visibilità pagina
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
    }

    setupChart() {
        const ctx = document.getElementById('powerChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Potenza Media (kW)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: true,
                    backgroundColor: 'rgba(75, 192, 192, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].parsed.x);
                                const endDate = new Date(date.getTime() + 15*60000);
                                return `Intervallo: ${date.toLocaleTimeString()} - ${endDate.toLocaleTimeString()}`;
                            },
                            label: function(context) {
                                return `Potenza Media: ${context.parsed.y.toFixed(2)} kW`;
                            }
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            stepSize: 15,
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Ora'
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Potenza Media (kW)'
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2) + ' kW';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    setupEventListeners() {
        // Gestione pulsanti 24h/48h
        document.querySelectorAll('[data-hours]').forEach(button => {
            button.addEventListener('click', (e) => {
                this.currentHours = parseInt(e.target.dataset.hours);
                // Aggiorna UI pulsanti
                document.querySelectorAll('[data-hours]').forEach(btn => 
                    btn.classList.toggle('active', btn === e.target));
                this.updateData();
            });
        });
    }

    async updateData() {
        try {
            const response = await fetch(`/api/plants/${this.plantId}/measurements/?hours=${this.currentHours}`);
            if (!response.ok) throw new Error('Errore nel recupero dei dati');
            
            const data = await response.json();
            const aggregatedData = this.aggregate15MinData(data.data);
            this.updateChart(aggregatedData);
            this.updateLastUpdate();
            
            if (data.plant_info) {
                this.updateConnectionStatus(data.plant_info.mqtt_status);
            }
        } catch (error) {
            console.error('Errore nell\'aggiornamento del grafico:', error);
            this.showError('Errore nel recupero dei dati');
        }
    }

    aggregate15MinData(rawData) {
        if (!rawData || !rawData.length) return { data: [] };

        const groupedData = {};
        
        rawData.forEach(measurement => {
            const date = new Date(measurement.timestamp);
            // Arrotonda al quarto d'ora più vicino
            date.setMinutes(Math.floor(date.getMinutes() / 15) * 15);
            date.setSeconds(0);
            date.setMilliseconds(0);
            
            const key = date.getTime();
            
            if (!groupedData[key]) {
                groupedData[key] = {
                    sum: 0,
                    count: 0,
                    timestamp: date,
                    min: measurement.power,
                    max: measurement.power
                };
            } else {
                groupedData[key].min = Math.min(groupedData[key].min, measurement.power);
                groupedData[key].max = Math.max(groupedData[key].max, measurement.power);
            }
            
            groupedData[key].sum += measurement.power;
            groupedData[key].count++;
        });

        // Calcola le medie e formatta i dati
        const aggregatedData = Object.values(groupedData).map(group => ({
            timestamp: group.timestamp,
            power: group.sum / group.count,
            min: group.min,
            max: group.max
        }));

        // Ordina per timestamp
        aggregatedData.sort((a, b) => a.timestamp - b.timestamp);

        return { data: aggregatedData };
    }

    updateChart(data) {
        if (!data.data || !data.data.length) {
            this.showError('Nessun dato disponibile');
            return;
        }

        this.chart.data.labels = data.data.map(d => d.timestamp);
        this.chart.data.datasets[0].data = data.data.map(d => d.power / 1000); // Converti in kW

        this.chart.update('none'); // Aggiorna senza animazione per performance migliori
    }

    updateConnectionStatus(status) {
        const statusBadge = document.querySelector('.mqtt-status .badge');
        if (!statusBadge) return;
        
        if (status && status.connected) {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Connesso';
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.textContent = 'Disconnesso';
        }
    }

    updateLastUpdate() {
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = `Ultimo aggiornamento: ${now.toLocaleTimeString()}`;
        }
    }

    showError(message) {
        console.error(message);
        // Implementa qui la visualizzazione dell'errore nell'UI
    }

    startUpdateInterval() {
        this.updateData(); // Aggiorna subito
        this.updateInterval = setInterval(() => this.updateData(), 60000); // Aggiorna ogni minuto
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
            this.updateData();
            this.startUpdateInterval();
        }
    }

    // Metodo per la pulizia quando si lascia la pagina
    destroy() {
        this.stopUpdateInterval();
        if (this.chart) {
            this.chart.destroy();
        }
        // Rimuovi event listeners
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    }
}

// Esporta la classe per l'uso
export default PowerChartManager;