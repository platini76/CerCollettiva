# core/views.py
from .views.dashboard import DashboardView, HomeView, CerDashboardView
from .views.cer import CERListView, CERDetailView, CERJoinView 
from .views.plant import (
    PlantListView, 
    PlantDetailView,
    PlantCreateView,
    PlantUpdateView,
    PlantMQTTConfigView
)
from .views.document import (
    PlantDocumentListView,
    PlantDocumentUploadView, 
    PlantDocumentDeleteView
)
from .views.gaudi import NewPlantFromGaudiView, PlantGaudiUpdateView
from .views.mqtt import mqtt_reconnect_view

# Esporta tutte le views
__all__ = [
    'DashboardView',
    'HomeView', 
    'CerDashboardView',
    'CERListView',
    'CERDetailView',
    'CERJoinView',
    'PlantListView',
    'PlantDetailView',
    'PlantCreateView', 
    'PlantUpdateView',
    'PlantMQTTConfigView',
    'PlantDocumentListView',
    'PlantDocumentUploadView',
    'PlantDocumentDeleteView',
    'NewPlantFromGaudiView',
    'PlantGaudiUpdateView',
    'mqtt_reconnect_view'
]