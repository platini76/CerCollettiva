# core/views/__init__.py
from .dashboard import DashboardView, HomeView, CerDashboardView
from .cer import CERListView, CERDetailView, CERJoinView
from .plant import (
    PlantListView,
    PlantDetailView,
    PlantCreateView,
    PlantUpdateView,
    PlantMQTTConfigView,
    plant_delete    
)
from .document import (
    PlantDocumentListView,
    PlantDocumentUploadView,
    PlantDocumentDeleteView
)
from .gaudi import NewPlantFromGaudiView, PlantGaudiUpdateView
from .mqtt import mqtt_reconnect_view

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