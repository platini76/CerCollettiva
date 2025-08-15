# energy/api/serializers.py
from rest_framework import serializers
from ..models import (
    DeviceMeasurement, 
    DeviceMeasurementDetail, 
    EnergyMeasurement, 
    EnergyAggregate,
    DeviceConfiguration
)
#from ..devices.models import DeviceConfiguration
from core.models import Plant  # Import diretto da core

class PlantSerializer(serializers.ModelSerializer):
    device_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Plant
        fields = [
            'id',
            'name',
            'pod_code',
            'plant_type',
            'owner',
            'cer_configuration',
            'nominal_power',
            'connection_voltage',
            'installation_date',
            'address',
            'city',
            'zip_code',
            'province',
            'is_active',
            'mqtt_connected',
            'created_at',
            'updated_at',
            'device_count'
        ]
        read_only_fields = [
            'owner',
            'mqtt_connected',
            'created_at',
            'updated_at',
            'device_count'
        ]

    def get_device_count(self, obj):
        return obj.devices.count() if hasattr(obj, 'devices') else 0

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Aggiungi il plant_type in formato display
        data['plant_type_display'] = instance.get_plant_type_display()
        # Se l'istanza ha una CER configurata, includi il suo nome
        if instance.cer_configuration:
            data['cer_configuration_name'] = instance.cer_configuration.name
        return data

class DeviceConfigurationSerializer(serializers.ModelSerializer):
    plant = PlantSerializer(read_only=True)
    
    class Meta:
        model = DeviceConfiguration
        fields = [
            'id', 'device_id', 'device_type', 'vendor', 'model',
            'mqtt_topic_template', 'is_active', 'plant', 'last_seen'
        ]

class DeviceMeasurementDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceMeasurementDetail
        fields = [
            'phase', 'voltage', 'current', 'power', 
            'power_factor', 'frequency', 'apparent_power', 'reactive_power'
        ]

class DeviceMeasurementSerializer(serializers.ModelSerializer):
    phase_details = DeviceMeasurementDetailSerializer(many=True, read_only=True)
    device = DeviceConfigurationSerializer(read_only=True)
    apparent_power = serializers.FloatField(read_only=True)
    reactive_power = serializers.FloatField(read_only=True)
    
    class Meta:
        model = DeviceMeasurement
        fields = [
            'id', 'timestamp', 'power', 'voltage', 'current',
            'energy_total', 'power_factor', 'quality', 
            'phase_details', 'apparent_power', 'reactive_power',
            'device'
        ]

class EnergyMeasurementSerializer(serializers.ModelSerializer):
    device = serializers.CharField(source='device_measurement.device.device_id')
    plant = serializers.CharField(source='device_measurement.plant.name')
    
    class Meta:
        model = EnergyMeasurement
        fields = [
            'id', 'timestamp', 'measurement_type', 'value',
            'unit', 'quality', 'device', 'plant'
        ]

class EnergyAggregateSerializer(serializers.ModelSerializer):
    device = DeviceConfigurationSerializer(read_only=True)
    net_energy = serializers.FloatField(read_only=True)
    
    class Meta:
        model = EnergyAggregate
        fields = [
            'id', 'period', 'start_time', 'end_time',
            'energy_in', 'energy_out', 'peak_power',
            'avg_power', 'net_energy', 'device'
        ]

# Serializzatori per richieste specifiche
class EnergyAggregateRequestSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    period = serializers.ChoiceField(
        choices=['15M', '1H', '1D', '1W', '1M'],
        default='1H'
    )