// static/energy/js/plant-detail.js
document.addEventListener('DOMContentLoaded', function() {
    // Funzionalità per la pagina di dettaglio impianto
    function updatePlantStatistics() {
        const plantId = document.getElementById('plant-detail').dataset.plantId;
        fetch(`/energy/api/plants/${plantId}/statistics/`)
            .then(response => response.json())
            .then(data => {
                // Aggiorna i valori nella pagina
                if (data) {
                    document.getElementById('total-power').textContent = data.total_power + ' W';
                    document.getElementById('device-count').textContent = data.device_count;
                    if (data.last_update) {
                        document.getElementById('last-update').textContent = new Date(data.last_update).toLocaleString();
                    }
                }
            })
            .catch(error => console.error('Errore nel caricamento delle statistiche:', error));
    }

    // Aggiorna le statistiche ogni minuto
    updatePlantStatistics();
    setInterval(updatePlantStatistics, 60000);
});