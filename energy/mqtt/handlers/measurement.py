# energy/mqtt/handlers/measurement.py
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseHandler
from ...devices.base.device import MeasurementData

logger = logging.getLogger(__name__)

class MeasurementHandler(BaseHandler):
    """Handler specializzato per messaggi di misurazione"""
    
    def _validate_message(self, topic: str, payload: Any) -> bool:
        """Validazione specifica per misurazioni"""
        if not topic or not payload:
            return False

        # Verifica che il topic sia nella forma corretta
        try:
            parts = topic.split('/')
            return len(parts) >= 3
        except Exception:
            return False

    def _parse_payload(self, payload: Any) -> Optional[Dict[str, Any]]:
        """Parse specializzato per dati di misurazione"""
        try:
            # Gestione diversi tipi di payload
            if isinstance(payload, bytes):
                try:
                    return json.loads(payload.decode('utf-8'))
                except UnicodeDecodeError:
                    return None
            elif isinstance(payload, str):
                return json.loads(payload)
            elif isinstance(payload, dict):
                return payload
            return None

        except json.JSONDecodeError:
            return None
        except Exception as e:
            error_key = f"parse_{str(e)}"
            if error_key not in self._logged_errors:
                logger.error(f"Payload parse error: {e}")
                self._logged_errors.add(error_key)
            return None

    def _process_measurement(self, data: Dict[str, Any]) -> Optional[MeasurementData]:
        """Processa i dati di misurazione"""
        try:
            # Verifica campi minimi richiesti
            if not all(key in data for key in ['power', 'voltage', 'current']):
                return None

            # Crea oggetto MeasurementData
            measurement = MeasurementData(
                timestamp=datetime.now(),
                power=self._safe_float(data['power']),
                voltage=self._safe_float(data['voltage']),
                current=self._safe_float(data['current']),
                energy=self._safe_float(data.get('energy', 0)),
                power_factor=self._safe_float(data.get('power_factor', 1.0)),
                frequency=self._safe_float(data.get('frequency', 50.0)),
                quality=data.get('quality', 'GOOD'),
                phase_data=data.get('phase_data', {}),
                extra_data=data.get('extra_data', {})
            )

            return measurement

        except Exception as e:
            logger.error(f"Error processing measurement: {e}")
            return None

    def _validate_measurement(self, data: MeasurementData) -> bool:
        """Validazione dei dati di misurazione"""
        try:
            return (
                data.power is not None and
                data.voltage is not None and
                data.current is not None and
                data.power_factor >= 0 and 
                data.power_factor <= 1
            )
        except Exception:
            return False