# energy/mqtt/handlers/device.py
import logging
from typing import Dict, Any, Optional
from django.db import transaction
from .base import BaseHandler
from ...models import DeviceMeasurement, DeviceMeasurementDetail, EnergyMeasurement
from ...devices.base.device import MeasurementData

logger = logging.getLogger(__name__)

class DeviceHandler(BaseHandler):
    """Handler per la gestione dei dispositivi"""

    def __init__(self):
        super().__init__()
        self._cached_pod_masks = {}

    @transaction.atomic
    def save_measurement(self, device_config: Any, data: MeasurementData) -> bool:
        """Salva una misurazione nel database"""
        try:
            if not device_config.plant:
                return False

            # Crea la misurazione principale
            measurement = self._create_measurement(device_config, data)

            # Salva i dettagli delle fasi
            if data.phase_data:
                self._save_phase_details(measurement, data.phase_data)

            # Crea record energia per potenze non zero
            if abs(data.power) > 0:
                self._create_energy_measurement(
                    measurement, 
                    device_config,
                    data
                )

            # Log con POD mascherato
            self._log_measurement(device_config, data)

            return True

        except Exception as e:
            logger.error(f"Error saving measurement: {e}")
            return False

    def _create_measurement(self, 
                          device_config: Any, 
                          data: MeasurementData) -> DeviceMeasurement:
        """Crea il record principale di misurazione"""
        return DeviceMeasurement.objects.create(
            plant=device_config.plant,
            device=device_config,
            timestamp=data.timestamp,
            power=data.power,
            voltage=data.voltage,
            current=data.current,
            energy_total=data.energy,
            power_factor=data.power_factor,
            quality=data.quality
        )

    def _save_phase_details(self, 
                          measurement: DeviceMeasurement,
                          phase_data: Dict[str, Dict[str, float]]) -> None:
        """Salva i dettagli delle fasi"""
        details = []
        for phase, data in phase_data.items():
            if all(key in data for key in ['voltage', 'current', 'power']):
                detail = DeviceMeasurementDetail(
                    measurement=measurement,
                    phase=phase,
                    voltage=data['voltage'],
                    current=data['current'],
                    power=data['power'],
                    power_factor=data.get('power_factor', 1.0),
                    frequency=data.get('frequency', 50.0)
                )
                details.append(detail)

        if details:
            DeviceMeasurementDetail.objects.bulk_create(details)

    def _create_energy_measurement(self,
                                measurement: DeviceMeasurement,
                                device_config: Any,
                                data: MeasurementData) -> None:
        """Crea il record di misurazione energetica"""
        EnergyMeasurement.objects.create(
            measurement_type='POWER_DRAW' if data.power >= 0 else 'POWER_IN',
            value=abs(data.power),
            unit='W',
            topic=device_config.mqtt_topic_template,
            device_measurement=measurement,
            quality=data.quality
        )

    def _log_measurement(self, device_config: Any, data: MeasurementData) -> None:
        """Log della misurazione con POD mascherato"""
        try:
            pod = getattr(device_config.plant, 'pod', 'N/A')
            
            # Usa cache per POD mascherati
            if pod not in self._cached_pod_masks:
                self._cached_pod_masks[pod] = (
                    f"{pod[:3]}...{pod[-3:]}" if len(pod) > 6 else "***"
                )
            
            masked_pod = self._cached_pod_masks[pod]
            
            #logger.info(
            #    f"Measurement saved - Device: {device_config.device_id} "
            #    f"[{masked_pod}] Power: {data.power:.1f}W"
            #)
            
        except Exception as e:
            logger.error(f"Error logging measurement: {e}")

    def get_device_info(self, device_config: Any) -> Dict[str, Any]:
        """Recupera informazioni sul dispositivo"""
        try:
            return {
                'id': device_config.device_id,
                'type': device_config.device_type,
                'plant': getattr(device_config.plant, 'name', 'Unknown'),
                'location': getattr(device_config.plant, 'location', 'Unknown'),
                'last_seen': device_config.last_seen
            }
        except Exception:
            return {}