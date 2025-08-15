// static/energy/js/plant-detail.js

const PlantDetail = {
    init() {
        this.plantId = document.querySelector('[data-plant-id]')?.dataset.plantId;
        if (!this.plantId) return;
        
        this.setupEventListeners();
        this.loadStatistics();
        this.setupRefreshInterval();
    },

    setupEventListeners() {
        // Refresh button click handler
        const refreshBtn = document.querySelector('.refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadStatistics());
        }
    },

    async loadStatistics() {
        try {
            const response = await fetch(`/api/plants/${this.plantId}/statistics/`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            this.updateUI(data);
        } catch (error) {
            console.error('Error loading plant statistics:', error);
        }
    },

    updateUI(data) {
        // Update statistics
        if (data.total_power !== undefined) {
            document.getElementById('plantTotalPower').textContent = `${data.total_power.toFixed(2)} kW`;
        }
        if (data.device_count !== undefined) {
            document.getElementById('plantDeviceCount').textContent = data.device_count;
        }
        if (data.last_update) {
            document.getElementById('plantLastUpdate').textContent = new Date(data.last_update).toLocaleString();
        }
    },

    setupRefreshInterval() {
        // Refresh data every minute
        setInterval(() => this.loadStatistics(), 60000);
    }
};

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => PlantDetail.init());