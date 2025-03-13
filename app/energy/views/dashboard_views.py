#energy/views/dashboard_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Max
from django.utils import timezone
from django.views.generic import TemplateView  # Import TemplateView
from datetime import timedelta
import logging
from core.models import Plant
from ..models import DeviceConfiguration, DeviceMeasurement
from ..mqtt.client import get_mqtt_client

logger = logging.getLogger(__name__)

@login_required
def total_power_data(request):
    """
    Recupera e formatta i dati di potenza per il grafico, con supporto per vari intervalli temporali
    e aggregazione dei dati.
    """
    try:
        now = timezone.localtime()
        time_range = request.GET.get('range', '5m')
        
        # Determina l'intervallo temporale e il periodo di aggregazione
        if time_range == '5m':
            time_threshold = now - timedelta(minutes=5)
            aggregation_minutes = 1
        elif time_range == '1h':
            time_threshold = now - timedelta(hours=1)
            aggregation_minutes = 5
        elif time_range == '24h':
            time_threshold = now - timedelta(days=1)
            aggregation_minutes = 15
        elif time_range == '48h':
            time_threshold = now - timedelta(days=2)
            aggregation_minutes = 30
        else:
            time_threshold = now - timedelta(minutes=5)
            aggregation_minutes = 1

        # Registra i parametri della query
        logger.info(f"Recupero dati potenza - Range: {time_range}, Soglia: {time_threshold}, Aggregazione: {aggregation_minutes} min")
        
        # Query base per le misurazioni
        measurements = DeviceMeasurement.objects.filter(
            timestamp__gte=time_threshold
        ).select_related('device', 'device__plant').order_by('timestamp')

        # Filtra per utente se non è staff
        if not request.user.is_staff:
            measurements = measurements.filter(plant__owner=request.user)
            
        # Log per debug
        count = measurements.count()
        logger.info(f"Trovate {count} misurazioni per il periodo selezionato")

        # Aggregazione dei dati
        data_points = {}
        for measurement in measurements:
            # Arrotonda il timestamp al periodo di aggregazione più vicino
            rounded_time = measurement.timestamp.replace(
                second=0, 
                microsecond=0,
                minute=(measurement.timestamp.minute // aggregation_minutes) * aggregation_minutes
            )
            
            if rounded_time not in data_points:
                data_points[rounded_time] = {
                    'power_sum': 0,
                    'count': 0
                }
            
            data_points[rounded_time]['power_sum'] += measurement.power
            data_points[rounded_time]['count'] += 1

        # Prepara i dati per il grafico
        timestamps = []
        values = []
        
        for timestamp in sorted(data_points.keys()):
            point = data_points[timestamp]
            avg_power = point['power_sum'] / point['count']
            
            timestamps.append(timestamp.isoformat())
            values.append(round(avg_power / 1000.0, 2))  # Converti in kW

        response_data = {
            'timestamps': timestamps,
            'values': values,
            'last_update': now.strftime('%H:%M:%S')
        }

        if measurements.exists():
            logger.info(f"Found {len(timestamps)} aggregated points for range {time_range}")
            logger.info(f"First timestamp: {timestamps[0] if timestamps else 'none'}")
            logger.info(f"First value: {values[0] if values else 'none'}")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in total_power_data: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'timestamps': [],
            'values': [],
            'last_update': now.strftime('%H:%M:%S')
        }, status=500)
    
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'energy/dashboard.html'

    # Rimuoviamo il controllo che obbliga l'utente ad essere admin
    # def dispatch(self, request, *args, **kwargs):
    #     if not request.user.is_staff:
    #         messages.error(request, 'Accesso consentito solo agli amministratori')
    #         return redirect('core:home')
    #     return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        time_threshold = now - timedelta(minutes=5)

        # Admin può vedere tutti gli impianti, utenti normali solo i propri
        if self.request.user.is_staff:
            plants = Plant.objects.all()  # L'admin vede tutti gli impianti
        else:
            plants = Plant.objects.filter(owner=self.request.user)  # Utenti normali vedono solo i propri

        logger.info("\n=== PLANT STATUS CHECK START ===")
        
        total_power = 0
        all_plant_devices = [] # List of all devices for all the plants
        for plant in plants:
             logger.info(f"\nPlant: {plant.name} (ID: {plant.id})")
             logger.info(f"Timestamp threshold: {time_threshold}")
             plant_devices = DeviceConfiguration.objects.filter(plant=plant).select_related('plant')
             all_plant_devices.extend(plant_devices)
             logger.info(f"\nDispositivi configurati per impianto:")
             
             for device in plant_devices:
                 logger.info(f"\nDevice Config:")
                 logger.info(f"- Device ID: {device.device_id}")
                 logger.info(f"- Topic template: {device.mqtt_topic_template}")
                 logger.info(f"- Is active: {device.is_active}")
                 
                 # Verifica ultime misurazioni
                 last_measurement = DeviceMeasurement.objects.filter(
                     device=device,
                     timestamp__gte=time_threshold
                 ).order_by('-timestamp').first()

                 if last_measurement:
                     logger.info(f"  Ultima misurazione:")
                     logger.info(f"  - Timestamp: {last_measurement.timestamp}")
                     logger.info(f"  - Power: {last_measurement.power}W")
                     total_power += last_measurement.power
                 else:
                     logger.info("  Nessuna misurazione recente trovata")
        
        logger.info(f"\nRiepilogo potenza:")
        logger.info(f"Potenza totale impianto: {total_power}W ({total_power/1000:.2f}kW)")

        try:
            # Query ottimizzata per dispositivi attivi e online
            active_devices = list(filter(lambda x: x.is_active, all_plant_devices))
            online_devices = DeviceMeasurement.objects.filter(
                device__in=active_devices,
                timestamp__gte=time_threshold
            ).values('device').distinct()

            total_active = len(active_devices)
            online_count = online_devices.count()
            
            logger.info(f"\nStatistiche dispositivi:")
            logger.info(f"- Totali: {len(all_plant_devices)}")
            logger.info(f"- Attivi: {total_active}")
            logger.info(f"- Online: {online_count}")

            # MQTT stats e stato
            client = get_mqtt_client()
            mqtt_status = "Connesso" if client and client.is_connected else "Disconnesso"
            
            # Calcola i dispositivi nuovi in base al ruolo dell'utente
            if self.request.user.is_staff:
                new_devices_query = DeviceConfiguration.objects.filter(
                    created_at__gte=now - timedelta(days=1)
                )
            else:
                new_devices_query = DeviceConfiguration.objects.filter(
                    plant__owner=self.request.user,
                    created_at__gte=now - timedelta(days=1)
                )
                
            device_stats = {
                'total_devices': len(all_plant_devices),
                'active_devices': total_active,
                'online_devices': online_count,
                'online_percentage': int((online_count / total_active * 100) if total_active > 0 else 0),
                'new_devices': new_devices_query.count()
            }

            # Query ottimizzata per i tipi di dispositivo
            if self.request.user.is_staff:
                device_types = (DeviceConfiguration.objects
                            .values('vendor', 'model')
                            .annotate(count=Count('id'))
                            .filter(count__gt=0)
                            .order_by('vendor', 'model'))
            else:
                device_types = (DeviceConfiguration.objects
                            .filter(plant__owner=self.request.user)
                            .values('vendor', 'model')
                            .annotate(count=Count('id'))
                            .filter(count__gt=0)
                            .order_by('vendor', 'model'))

            context.update({
                **device_stats,
                'device_types': device_types,
                'system_alerts': [],
                'mqtt_stats': {
                    'messages': DeviceMeasurement.objects.all().count() if self.request.user.is_staff else DeviceMeasurement.objects.filter(
                        device__plant__owner=self.request.user
                    ).count(),
                    'errors': 0,
                    'status': mqtt_status
                },
                'device_status': {
                    'total': device_stats['total_devices'],
                    'active': device_stats['active_devices'],
                    'online': device_stats['online_devices'],
                },
                'total_power': round(total_power / 1000.0, 2)  # Converti in kW
            })

            logger.info("\n=== PLANT STATUS CHECK END ===\n")

        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche dashboard: {str(e)}")
            logger.exception(e)  # Questo loggerà il traceback completo
            messages.error(self.request, "Errore nel caricamento delle statistiche")
            context.update({
                'error': True,
                'device_types': [],
                'system_alerts': [],
                'mqtt_stats': {'messages': 0, 'errors': 0, 'status': 'Errore'},
                'device_status': {'total': 0, 'active': 0, 'online': 0},
                'total_power': 0
            })

        return context
