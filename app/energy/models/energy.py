# energy/models/energy.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from .base import BaseMeasurementModel
from .device import DeviceMeasurement, DeviceConfiguration

class EnergyInterval(models.Model):
    """Misurazioni di energia per intervalli di 15 minuti"""
    device = models.ForeignKey(
        'energy.DeviceConfiguration',
        on_delete=models.CASCADE,
        related_name='energy_intervals'
    )
    start_time = models.DateTimeField(
        help_text="Inizio dell'intervallo di misurazione"
    )
    end_time = models.DateTimeField(
        help_text="Fine dell'intervallo di misurazione"
    )
    energy_value = models.FloatField(
        help_text="Energia misurata nell'intervallo in kWh",
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Intervallo Energia"
        verbose_name_plural = "Intervalli Energia"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['device', 'start_time']),
            models.Index(fields=['device', 'end_time']),
            models.Index(fields=['start_time', 'end_time'])
        ]
        unique_together = ['device', 'start_time']

    def __str__(self):
        return (
            f"{self.device.device_id} - "
            f"{self.start_time.strftime('%Y-%m-%d %H:%M')} - "
            f"{self.energy_value:.2f} kWh"
        )

    @property
    def interval_duration(self) -> int:
        """Restituisce la durata dell'intervallo in minuti"""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def is_valid_interval(self) -> bool:
        """Verifica se l'intervallo è valido (15 minuti)"""
        return self.interval_duration == 15 and self.energy_value >= 0

class EnergyMeasurement(BaseMeasurementModel):
    """Misurazioni di energia"""
    
    MEASUREMENT_TYPES = [
        ('POWER_DRAW', 'Prelievo'),
        ('POWER_IN', 'Immissione'),
        ('ENERGY_TOTAL', 'Energia Totale'),
        ('ENERGY_RETURNED', 'Energia Restituita')
    ]

    UNIT_CHOICES = [
        ('W', 'Watt'),
        ('kW', 'Kilowatt'),
        ('kWh', 'Kilowattora'),
        ('Wh', 'Wattora')
    ]

    measurement_type = models.CharField(
        max_length=20,
        choices=MEASUREMENT_TYPES,
        help_text="Tipo di misurazione energetica"
    )
    value = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Valore della misurazione"
    )
    unit = models.CharField(
        max_length=5,
        choices=UNIT_CHOICES,
        default='W',
        help_text="Unità di misura"
    )
    topic = models.CharField(
        max_length=255,
        help_text="Topic MQTT di origine"
    )
    device_measurement = models.ForeignKey(
        DeviceMeasurement,
        on_delete=models.CASCADE,
        related_name='energy_measurements'
    )

    class Meta:
        verbose_name = "Misurazione Energia"
        verbose_name_plural = "Misurazioni Energia"
        indexes = [
            models.Index(fields=['measurement_type', 'timestamp']),
            models.Index(fields=['topic', 'timestamp'])
        ]

    def __str__(self):
        return (
            f"{self.measurement_type} - {self.value} {self.unit} - "
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def convert_to_kwh(self) -> float:
        """Converte il valore in kWh"""
        if self.unit == 'kWh':
            return self.value
        elif self.unit == 'Wh':
            return self.value / 1000
        elif self.unit == 'W':
            # Converti assumendo 1 ora di misurazione
            return self.value / 1000
        elif self.unit == 'kW':
            return self.value
        return 0

class EnergyAggregate(BaseMeasurementModel):
    """Aggregazioni di misurazioni energetiche"""
    
    PERIOD_CHOICES = [
        ('15M', '15 Minuti'),
        ('1H', '1 Ora'),
        ('1D', '1 Giorno'),
        ('1W', '1 Settimana'),
        ('1M', '1 Mese')
    ]

    period = models.CharField(
        max_length=3,
        choices=PERIOD_CHOICES,
        help_text="Periodo di aggregazione"
    )
    start_time = models.DateTimeField(
        help_text="Inizio del periodo"
    )
    end_time = models.DateTimeField(
        help_text="Fine del periodo"
    )
    device = models.ForeignKey(
        'energy.DeviceConfiguration',
        on_delete=models.CASCADE,
        related_name='energy_aggregates'
    )
    
    # Valori aggregati
    energy_in = models.FloatField(
        default=0,
        help_text="Energia immessa in kWh"
    )
    energy_out = models.FloatField(
        default=0,
        help_text="Energia prelevata in kWh"
    )
    peak_power = models.FloatField(
        null=True,
        help_text="Picco di potenza nel periodo in W"
    )
    avg_power = models.FloatField(
        null=True,
        help_text="Potenza media nel periodo in W"
    )

    class Meta:
        verbose_name = "Aggregazione Energia"
        verbose_name_plural = "Aggregazioni Energia"
        indexes = [
            models.Index(fields=['device', 'period', 'start_time']),
            models.Index(fields=['period', 'start_time'])
        ]
        unique_together = ['device', 'period', 'start_time']

    def __str__(self):
        return (
            f"{self.device.device_id} - {self.period} - "
            f"{self.start_time.strftime('%Y-%m-%d %H:%M')}"
        )

    @property
    def net_energy(self) -> float:
        """Calcola l'energia netta (immessa - prelevata)"""
        return self.energy_in - self.energy_out

    def is_complete(self) -> bool:
        """Verifica se l'aggregazione è completa"""
        return self.end_time <= timezone.now()

# Modelli per la gestione del Settlement CER
class CERSettlement(models.Model):
    """
    Settlement economico delle CER
    Tiene traccia dei benefici economici della CER nel suo insieme
    """
    cer = models.ForeignKey(
        'core.CERConfiguration', 
        on_delete=models.CASCADE, 
        related_name='settlements',
        verbose_name="Comunità Energetica"
    )
    
    # Periodo di settlement
    period_start = models.DateTimeField(
        verbose_name="Inizio Periodo",
        help_text="Inizio del periodo di settlement"
    )
    period_end = models.DateTimeField(
        verbose_name="Fine Periodo",
        help_text="Fine del periodo di settlement"
    )
    
    # Dati energetici e incentivi
    total_shared_energy = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Energia Condivisa",
        help_text="kWh condivisi totali nella CER"
    )
    total_incentive = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Incentivo Totale",
        help_text="Incentivo totale in €"
    )
    unit_incentive = models.DecimalField(
        max_digits=8, 
        decimal_places=5, 
        default=0,
        verbose_name="Incentivo Unitario",
        help_text="Incentivo unitario in €/kWh"
    )
    
    # Stato del settlement
    STATUS_CHOICES = [
        ('DRAFT', 'Bozza'),
        ('FINALIZED', 'Finalizzato'),
        ('APPROVED', 'Approvato'),
        ('DISTRIBUTED', 'Distribuito'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='DRAFT',
        verbose_name="Stato",
        help_text="Stato attuale del settlement"
    )
    
    # Chi ha creato/approvato il settlement
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_settlements',
        verbose_name="Creato Da"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_settlements',
        verbose_name="Approvato Da"
    )
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Settlement CER"
        verbose_name_plural = "Settlement CER"
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['cer', 'period_start', 'period_end']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"CER {self.cer.name} - {self.period_start.strftime('%Y-%m')} - {self.status}"
    
    @property
    def period_name(self):
        """Nome leggibile del periodo"""
        if self.period_start.month == self.period_end.month and self.period_start.year == self.period_end.year:
            return self.period_start.strftime('%B %Y')
        return f"{self.period_start.strftime('%b %Y')} - {self.period_end.strftime('%b %Y')}"
        
    @property
    def is_editable(self):
        """Verifica se il settlement è ancora modificabile"""
        return self.status in ['DRAFT', 'FINALIZED']

class MemberSettlement(models.Model):
    """
    Settlement economico dei singoli membri della CER
    Contiene i dettagli di energia e incentivi per ciascun membro
    """
    settlement = models.ForeignKey(
        CERSettlement, 
        on_delete=models.CASCADE, 
        related_name='member_settlements',
        verbose_name="Settlement"
    )
    membership = models.ForeignKey(
        'core.CERMembership', 
        on_delete=models.CASCADE, 
        related_name='settlements',
        verbose_name="Membro CER"
    )
    
    # Dati energetici
    produced = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Energia Prodotta",
        help_text="kWh prodotti dal membro"
    )
    consumed = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Energia Consumata",
        help_text="kWh consumati dal membro"
    )
    fed_in = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Energia Immessa",
        help_text="kWh immessi in rete dal membro"
    )
    self_consumed = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Autoconsumo",
        help_text="kWh autoconsumati dal membro"
    )
    shared = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name="Energia Condivisa",
        help_text="kWh condivisi con la CER"
    )
    
    # Incentivi e benefici economici
    incentive_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Incentivo",
        help_text="€ di incentivo"
    )
    grid_savings = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Risparmio Rete",
        help_text="€ risparmiati da oneri di rete"
    )
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Settlement Membro"
        verbose_name_plural = "Settlement Membri"
        unique_together = ('settlement', 'membership')
    
    def __str__(self):
        return f"{self.membership.user.username} - {self.settlement.period_name}"
    
    @property
    def total_benefit(self):
        """Beneficio economico totale"""
        return self.incentive_amount + self.grid_savings