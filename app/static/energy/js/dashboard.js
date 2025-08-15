// Funzionalità dashboard
const Dashboard = {
    init: function() {
        console.log('Dashboard initialized');
        this.setupCharts();
        this.setupRefreshInterval();
        this.setupRangeControls();
    },

    setupCharts: function() {
        // Implementa i grafici della dashboard
        this.setupEnergyChart();
        this.setupConsumptionChart();
        this.setupSettlementChart();
    },

    setupEnergyChart: function() {
        // Implementa il grafico dell'energia
        const ctx = document.getElementById('energyChart');
        if (ctx) {
            this.energyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Potenza (kW)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Potenza (kW)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Ora'
                            }
                        }
                    }
                }
            });
            this.refreshData('5m'); // Carica inizialmente dati per 5 minuti
        }
    },

    setupConsumptionChart: function() {
        // Implementa il grafico dei consumi
        const ctx = document.getElementById('consumptionChart');
        if (ctx) {
            this.consumptionChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Prodotta', 'Consumata', 'Condivisa', 'Immessa'],
                    datasets: [{
                        label: 'Energia (kWh)',
                        data: [0, 0, 0, 0],
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.5)',
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)'
                        ],
                        borderColor: [
                            'rgb(75, 192, 192)',
                            'rgb(255, 99, 132)',
                            'rgb(54, 162, 235)',
                            'rgb(255, 206, 86)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Energia (kWh)'
                            }
                        }
                    }
                }
            });
        }
    },

    setupSettlementChart: function() {
        // Implementa il grafico per i benefici economici
        const ctx = document.getElementById('settlementChart');
        if (ctx) {
            this.settlementChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno'],
                    datasets: [{
                        label: 'Benefici Economici (€)',
                        data: [0, 0, 0, 0, 0, 0],
                        backgroundColor: 'rgba(153, 102, 255, 0.5)',
                        borderColor: 'rgb(153, 102, 255)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Benefici Economici (€)'
                            }
                        }
                    }
                }
            });
        }
    },

    setupRangeControls: function() {
        // Setup dei controlli per il range temporale
        const rangeButtons = document.querySelectorAll('[data-range]');
        if (rangeButtons.length > 0) {
            rangeButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    const range = button.getAttribute('data-range');
                    this.refreshData(range);
                    
                    // Aggiorna il testo del pulsante dropdown
                    const dropdownButton = document.getElementById('periodDropdown');
                    if (dropdownButton) {
                        let labelText = 'Periodo';
                        switch(range) {
                            case '5m': labelText = 'Ultimi 5 minuti'; break;
                            case '1h': labelText = 'Ultima ora'; break;
                            case '24h': labelText = 'Ultime 24 ore'; break;
                            case '48h': labelText = 'Ultimi 2 giorni'; break;
                        }
                        dropdownButton.textContent = labelText;
                    }
                });
            });
        }
        
        // Carica anche i dati di settlement
        this.loadSettlementData();
    },

    setupRefreshInterval: function() {
        // Aggiorna i dati ogni minuto
        setInterval(() => {
            const activeRange = document.querySelector('.active-range')?.getAttribute('data-range') || '5m';
            this.refreshData(activeRange);
        }, 60000);
    },

    refreshData: function(range = '5m') {
        // Aggiorna i dati della dashboard
        fetch(`/api/dashboard/data/?range=${range}`)
            .then(response => response.json())
            .then(data => {
                this.updateEnergyChart(data);
                this.updateConsumptionData();
            })
            .catch(error => console.error('Error refreshing dashboard:', error));
    },

    updateEnergyChart: function(data) {
        // Aggiorna il grafico dell'energia
        if (this.energyChart && data.timestamps && data.values) {
            // Formatta le etichette temporali
            const labels = data.timestamps.map(ts => {
                const date = new Date(ts);
                return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            });
            
            this.energyChart.data.labels = labels;
            this.energyChart.data.datasets[0].data = data.values;
            this.energyChart.update();
            
            // Aggiorna l'ultimo aggiornamento
            const lastUpdateElement = document.getElementById('lastUpdate');
            if (lastUpdateElement) {
                lastUpdateElement.textContent = data.last_update;
            }
        }
    },

    updateConsumptionData: function() {
        // Recupera e aggiorna i dati di consumo
        fetch('/api/energy/consumption/')
            .then(response => response.json())
            .then(data => {
                if (this.consumptionChart && data.consumption) {
                    this.consumptionChart.data.datasets[0].data = [
                        data.consumption.produced || 0,
                        data.consumption.consumed || 0,
                        data.consumption.shared || 0,
                        data.consumption.fed_in || 0
                    ];
                    this.consumptionChart.update();
                }
            })
            .catch(error => console.error('Error updating consumption data:', error));
    },

    loadSettlementData: function() {
        // Carica i dati di settlement per i benefici economici
        fetch('/api/energy/settlement/')
            .then(response => response.json())
            .then(data => {
                if (this.settlementChart && data.settlements) {
                    this.settlementChart.data.labels = data.settlements.map(item => item.month);
                    this.settlementChart.data.datasets[0].data = data.settlements.map(item => item.benefit);
                    this.settlementChart.update();
                    
                    // Aggiorna anche la tabella del settlement se presente
                    this.updateSettlementTable(data.settlements);
                }
            })
            .catch(error => console.error('Error loading settlement data:', error));
    },
    
    updateSettlementTable: function(settlements) {
        const tableBody = document.querySelector('#settlementTable tbody');
        if (tableBody && settlements && settlements.length > 0) {
            tableBody.innerHTML = '';
            settlements.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.month}</td>
                    <td>${item.produced.toFixed(2)} kWh</td>
                    <td>${item.consumed.toFixed(2)} kWh</td>
                    <td>${item.shared.toFixed(2)} kWh</td>
                    <td>${item.benefit.toFixed(2)} €</td>
                `;
                tableBody.appendChild(row);
            });
        }
    }
};

// Inizializza la dashboard quando il documento è pronto
document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
});