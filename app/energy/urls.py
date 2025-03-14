# energy/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.dashboard_views import DashboardView, total_power_data
from .views.plant_views import (
    PlantListView, 
    PlantDetailView, 
    PlantCreateView, 
    plant_delete, 
    plant_mqtt_data
)
from .views.device_views import (
    DeviceListView, 
    DeviceDetailView, 
    DeviceCreateView, 
    MeasurementListView, 
    MeasurementDetailView, 
    device_delete
)
from .views.mqtt_views import mqtt_settings, mqtt_control, save_mqtt_settings
from .views.settlement_views import (
    settlement_dashboard,
    settlement_detail,
    settlement_new,
    settlement_create,
    settlement_action,
    settlement_member_view,
    api_settlement_list,
    api_settlement_detail,
    api_member_settlements,
    api_dashboard_summary
)
from .views.api import PlantViewSet, DeviceConfigurationViewSet, DeviceMeasurementViewSet

app_name = 'energy'

# Configurazione Router API REST
router = DefaultRouter()
router.register(r'plants', PlantViewSet, basename='api-plant')
router.register(r'devices', DeviceConfigurationViewSet, basename='api-device')
router.register(r'measurements', DeviceMeasurementViewSet, basename='api-measurement')

urlpatterns = [
    # Vista Dashboard principale
    path('', DashboardView.as_view(), name='dashboard'),

    # Gestione Impianti
    path('plants/', PlantListView.as_view(), name='plants'),
    path('plants/create/', PlantCreateView.as_view(), name='plant-create'),
    path('plants/<int:pk>/', PlantDetailView.as_view(), name='plant-detail'),
    path('plants/<int:pk>/delete/', plant_delete, name='plant-delete'),

    # Gestione Dispositivi
    path('devices/', DeviceListView.as_view(), name='devices'),
    path('devices/create/', DeviceCreateView.as_view(), name='device-create'),
    path('devices/<int:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('devices/<int:pk>/delete/', device_delete, name='device-delete'),

    # Gestione Misurazioni
    path('measurements/', MeasurementListView.as_view(), name='measurement-list'),
    path('measurements/<int:pk>/', MeasurementDetailView.as_view(), name='measurement-detail'),

    # Gestione Settlements CER
    path('settlements/', settlement_dashboard, name='settlements'),
    path('settlements/new/', settlement_new, name='settlement_new'),
    path('settlements/create/', settlement_create, name='settlement_create'),
    path('settlements/<int:settlement_id>/', settlement_detail, name='settlement_detail'),
    path('settlements/<int:settlement_id>/action/', settlement_action, name='settlement_action'),
    path('settlements/member/', settlement_member_view, name='settlement_member'),
    
    # Configurazione MQTT
    path('settings/mqtt/', mqtt_settings, name='mqtt_settings'),
    path('settings/mqtt/save/', save_mqtt_settings, name='save_mqtt_settings'),
    path('settings/mqtt/control/', mqtt_control, name='mqtt_control'),

    # API MQTT Data - Messo al livello principale
    path('api/plants/<int:plant_id>/mqtt-data/', plant_mqtt_data, name='plant-mqtt-data'),
    path('api/plants/mqtt-data/', plant_mqtt_data, name='mqtt-data'),

    # API Dispositivi
    path('api/devices/<int:pk>/latest_measurement/',
         DeviceConfigurationViewSet.as_view({'get': 'latest_measurement'}),
         name='api-device-latest-measurement'),
    path('api/measurements/latest/',
         DeviceMeasurementViewSet.as_view({'get': 'latest'}),
         name='api-measurements-latest'),
         
    # API Dati di Potenza e Dashboard
    path('api/dashboard/data/', total_power_data, name='total-power-data'),
    path('api/dashboard/summary/', api_dashboard_summary, name='dashboard-summary'),
    
    # API Settlement
    path('api/settlements/', api_settlement_list, name='api-settlements'),
    path('api/settlements/<int:settlement_id>/', api_settlement_detail, name='api-settlement-detail'),
    path('api/member-settlements/', api_member_settlements, name='api-member-settlements'),
    path('api/energy/settlement/', api_dashboard_summary, name='api-settlement'),
    path('api/energy/consumption/', api_dashboard_summary, name='api-consumption'),

    # Inclusione delle API REST standard come ultimo pattern
    path('api/', include(router.urls)),
]