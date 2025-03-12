# energy/models/__init__.py
# Importazioni base
from .device import DeviceType, DeviceConfiguration, DeviceMeasurement, DeviceMeasurementDetail
from .energy import EnergyMeasurement, EnergyAggregate, EnergyInterval
from .mqtt import MQTTBroker, MQTTConfiguration
from .audit import MQTTAuditLog

# Soluzione più semplice e compatibile per la retrocompatibilità con Device
# Fornisce un alias per DeviceConfiguration
Device = DeviceConfiguration

__all__ = [
    'Device',
    'DeviceType',
    'DeviceConfiguration',
    'DeviceMeasurement',
    'DeviceMeasurementDetail',
    'EnergyMeasurement',
    'EnergyAggregate',
    'EnergyInterval',
    'MQTTBroker',
    'MQTTConfiguration',
    'MQTTAuditLog',
]