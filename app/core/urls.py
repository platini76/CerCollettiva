from django.urls import path
from django.contrib import admin
from .admin import admin_site
from .views.gaudi import PlantCreateFromGaudiView
from .views import (
    # Views base
    HomeView,
    DashboardView,
    CerDashboardView,
    
    # Views CER
    CERListView,
    CERDetailView,
    CERJoinView,
    CERCreateView,
    CERDistributionSettingsView,
    
    # Views Plant
    PlantListView,
    PlantDetailView,
    PlantCreateView,
    PlantUpdateView,
    PlantMQTTConfigView,
    plant_delete,

    # Views Gaudì
    PlantDocumentListView,
    PlantDocumentUploadView,
    PlantDocumentDeleteView,
    NewPlantFromGaudiView,
    PlantGaudiUpdateView
)

from .views.api import (
    get_plant_data,
    plant_measurements_api,
    cer_power_api,
    mqtt_status_api
)

app_name = 'core'

urlpatterns = [
    # Home e Dashboard
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # CER URLs
    path('cer/', CERListView.as_view(), name='cer_list'),
    path('cer/create/', CERCreateView.as_view(), name='cer_create'),
    path('cer/<int:pk>/', CERDetailView.as_view(), name='cer_detail'),
    path('cer/<int:pk>/join/', CERJoinView.as_view(), name='cer_join'),
    path('cer/<int:pk>/distribution/', CERDistributionSettingsView.as_view(), name='cer_distribution_settings'),
    
    # Plant URLs - Base Operations
    path('plants/', PlantListView.as_view(), name='plant_list'),
    path('plants/create/', PlantCreateView.as_view(), name='plant_create'),
    path('plants/<int:pk>/', PlantDetailView.as_view(), name='plant_detail'),
    path('plants/<int:pk>/update/', PlantUpdateView.as_view(), name='plant_update'),
    path('plants/<int:pk>/delete/', plant_delete, name='plant_delete'),

    # Plant URLs - Gaudì Operations
    path('plants/new-from-gaudi/', NewPlantFromGaudiView.as_view(), name='plant_new_from_gaudi'),
    path('plants/create-from-gaudi/', PlantCreateFromGaudiView.as_view(), name='plant_create_with_gaudi'),
    path('plants/<int:pk>/gaudi-update/', PlantGaudiUpdateView.as_view(), name='plant_gaudi_update'),

    # Plant URLs - MQTT Configuration
    path('plants/<int:pk>/mqtt/', PlantMQTTConfigView.as_view(), name='plant_mqtt_config'),
    
    # Plant URLs - Document Management
    path('plants/<int:pk>/documents/', PlantDocumentListView.as_view(), name='plant_documents'),
    path('plants/<int:pk>/documents/upload/', PlantDocumentUploadView.as_view(), name='plant_document_upload'),
    path('plants/<int:pk>/documents/<int:document_id>/delete/', 
         PlantDocumentDeleteView.as_view(), 
         name='plant_document_delete'),
    
    # API URLs - Moved these to the top of API section for clarity
    path('api/plants/<int:pk>/data/', get_plant_data, name='api_plant_data'),
    path('api/plants/<int:plant_id>/measurements/', plant_measurements_api, name='plant-measurements-api'),
    path('api/cer-power/', cer_power_api, name='cer-power-api'),
    path('api/mqtt/status/<int:plant_id>/', mqtt_status_api, name='mqtt-status-api')
]