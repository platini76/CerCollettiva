# energy/services/energy_calculator_settlement.py
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.conf import settings

from core.models import CERConfiguration, CERMembership, Plant
from ..models.energy import CERSettlement, MemberSettlement, EnergyAggregate

logger = logging.getLogger('energy.settlement')

class CERSettlementCalculator:
    """
    Calcolatore per il settlement economico delle CER
    Implementa gli algoritmi di calcolo dei benefici economici per i membri CER
    """
    
    # Costanti per il calcolo degli incentivi (valori in €/kWh)
    DEFAULT_INCENTIVE_RATE = Decimal('0.118')  # 118 €/MWh (valore GSE per CER)
    DEFAULT_GRID_SAVINGS = Decimal('0.0095')   # 9.5 €/MWh (risparmio medio oneri di rete)
    
    # Frazioni di ripartizione di default
    DEFAULT_PRODUCER_SHARE = Decimal('0.7')    # 70% ai produttori
    DEFAULT_CONSUMER_SHARE = Decimal('0.3')    # 30% ai consumatori
    
    def __init__(self, cer_id=None):
        """
        Inizializza il calcolatore con una CER specifica se fornita
        
        Args:
            cer_id: ID opzionale della CER per cui calcolare il settlement
        """
        self.cer_id = cer_id
        self._init_rates()
        self._init_logger()
    
    def _init_rates(self):
        """Inizializza le tariffe di incentivazione"""
        # Se abbiamo una CER specifica, carica le tariffe dalla configurazione
        if self.cer_id:
            try:
                from core.models import CERConfiguration
                cer_config = CERConfiguration.objects.get(id=self.cer_id)
                
                self.incentive_rate = cer_config.incentive_rate
                self.grid_savings_rate = cer_config.grid_savings_rate
                self.producer_share = cer_config.producer_share / Decimal('100.0')
                self.consumer_share = cer_config.consumer_share / Decimal('100.0')
                self.admin_share = cer_config.admin_share / Decimal('100.0')
                self.investment_fund_share = cer_config.investment_fund_share / Decimal('100.0')
                self.solidarity_fund_share = cer_config.solidarity_fund_share / Decimal('100.0')
                self.legal_fund_share = cer_config.legal_fund_share / Decimal('100.0')
                
                logger.info(f"Tariffe caricate da CER {cer_config.name}: Incentivo={self.incentive_rate}€/kWh, "
                           f"Risparmio rete={self.grid_savings_rate}€/kWh, "
                           f"Quota Produttori={cer_config.producer_share}%, "
                           f"Quota Consumatori={cer_config.consumer_share}%")
                return
            except Exception as e:
                logger.warning(f"Impossibile caricare le tariffe dalla CER {self.cer_id}: {str(e)}. "
                              "Verranno utilizzati i valori predefiniti.")
                
        # Se non abbiamo una CER o c'è stato un errore, usa i valori predefiniti
        self.incentive_rate = self.DEFAULT_INCENTIVE_RATE
        self.grid_savings_rate = self.DEFAULT_GRID_SAVINGS
        self.producer_share = self.DEFAULT_PRODUCER_SHARE
        self.consumer_share = self.DEFAULT_CONSUMER_SHARE
        
        logger.info(f"Tariffe inizializzate (predefinite): Incentivo={self.incentive_rate}€/kWh, "
                  f"Risparmio rete={self.grid_savings_rate}€/kWh, "
                  f"Quota Produttori={self.producer_share*100}%, "
                  f"Quota Consumatori={self.consumer_share*100}%")
    
    def _init_logger(self):
        """Configurazione logger"""
        self.logger = logging.getLogger('energy.settlement')
        self.logger.setLevel(logging.INFO)
    
    def calculate_monthly_settlement(self, year, month, cer_id=None, user_id=None):
        """
        Calcola il settlement mensile per una CER
        
        Args:
            year: Anno di riferimento
            month: Mese di riferimento (1-12)
            cer_id: ID opzionale della CER (altrimenti usa quella impostata nel costruttore)
            user_id: ID utente che richiede il calcolo
            
        Returns:
            dict: Risultato del settlement con dettagli per membri
        """
        cer_id = cer_id or self.cer_id
        if not cer_id:
            raise ValueError("È necessario specificare una CER per il calcolo del settlement")
        
        try:
            cer = CERConfiguration.objects.get(id=cer_id)
        except CERConfiguration.DoesNotExist:
            raise ValueError(f"CER con ID {cer_id} non trovata")
        
        # Calcola periodo
        period_start = datetime(year, month, 1, 0, 0, 0)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
        
        self.logger.info(f"Calcolo settlement per CER {cer.name} - periodo: {period_start.strftime('%Y-%m')}")
        
        # Verifica se esiste già un settlement per questo periodo
        existing = CERSettlement.objects.filter(
            cer=cer,
            period_start=period_start,
            period_end=period_end
        ).first()
        
        if existing and existing.status not in ['DRAFT']:
            self.logger.warning(f"Settlement già esistente con stato {existing.status}")
            return self._format_settlement_results(existing)
        
        # Se non esiste o è in bozza, calcoliamo/ricalicoliamo
        with transaction.atomic():
            if existing:
                settlement = existing
                # Cancella i settlement dei membri esistenti per ricrearli
                settlement.member_settlements.all().delete()
            else:
                # Crea nuovo settlement
                settlement = CERSettlement.objects.create(
                    cer=cer,
                    period_start=period_start,
                    period_end=period_end,
                    status='DRAFT',
                    created_by_id=user_id,
                    unit_incentive=self.incentive_rate
                )
            
            # Ottiene membri e relativi impianti
            members = CERMembership.objects.filter(
                cer=cer,
                is_active=True,
                # La data di adesione deve essere precedente alla fine del periodo
                effective_date__lte=period_end
            ).select_related('user')
            
            if not members.exists():
                self.logger.warning(f"Nessun membro attivo trovato per la CER {cer.name} nel periodo {period_start.strftime('%Y-%m')}")
                return self._format_settlement_results(settlement)
            
            # Calcola i dati di energia condivisa e benefici
            shared_energy, member_data = self._calculate_shared_energy(cer, members, period_start, period_end)
            
            # Aggiorna il settlement principale
            settlement.total_shared_energy = shared_energy
            settlement.total_incentive = shared_energy * self.incentive_rate
            settlement.save()
            
            # Crea i settlement per ciascun membro
            for membership_id, data in member_data.items():
                MemberSettlement.objects.create(
                    settlement=settlement,
                    membership_id=membership_id,
                    produced=data['produced'],
                    consumed=data['consumed'],
                    fed_in=data['fed_in'],
                    self_consumed=data['self_consumed'],
                    shared=data['shared'],
                    incentive_amount=data['incentive'],
                    grid_savings=data['grid_savings']
                )
            
            return self._format_settlement_results(settlement)
    
    def _calculate_shared_energy(self, cer, members, period_start, period_end):
        """
        Calcola l'energia condivisa e i benefici per ciascun membro
        
        Args:
            cer: Oggetto CERConfiguration
            members: QuerySet di CERMembership
            period_start: Data/ora inizio periodo
            period_end: Data/ora fine periodo
            
        Returns:
            tuple: (energia_condivisa_totale, dati_membri)
        """
        # Inizializza strutture dati
        member_data = {}
        for member in members:
            member_data[member.id] = {
                'membership': member,
                'produced': Decimal('0'),
                'consumed': Decimal('0'),
                'fed_in': Decimal('0'),
                'self_consumed': Decimal('0'),
                'shared': Decimal('0'),
                'incentive': Decimal('0'),
                'grid_savings': Decimal('0')
            }
        
        # Ottieni tutti gli impianti associati ai membri
        plants = Plant.objects.filter(cer=cer)
        
        if not plants.exists():
            self.logger.warning(f"Nessun impianto trovato per la CER {cer.name}")
            return Decimal('0'), member_data
        
        # Per ogni impianto, ottieni le aggregazioni energetiche
        for plant in plants:
            membership = None
            try:
                # Trova membership associata al proprietario dell'impianto
                membership = CERMembership.objects.get(
                    cer=cer,
                    user=plant.owner,
                    is_active=True
                )
            except CERMembership.DoesNotExist:
                self.logger.warning(f"Proprietario dell'impianto {plant.name} non è membro della CER {cer.name}")
                continue
            
            # Ottieni i dispositivi dell'impianto
            devices = plant.devices.filter(is_active=True)
            
            # Per ogni dispositivo, ottieni le aggregazioni mensili
            for device in devices:
                # Calcola i timestamp per il filtraggio
                aggregates = EnergyAggregate.objects.filter(
                    device=device,
                    period='1D',  # Aggregazioni giornaliere
                    start_time__gte=period_start,
                    end_time__lte=period_end
                )
                
                # Somma i valori per il dispositivo
                for agg in aggregates:
                    member_data[membership.id]['produced'] += Decimal(str(agg.energy_in))
                    member_data[membership.id]['consumed'] += Decimal(str(agg.energy_out))
                    
                    # Calcola l'energia autoconsumata e quella immessa in rete
                    self_cons = min(Decimal(str(agg.energy_in)), Decimal(str(agg.energy_out)))
                    fed_in = max(Decimal('0'), Decimal(str(agg.energy_in)) - Decimal(str(agg.energy_out)))
                    
                    member_data[membership.id]['self_consumed'] += self_cons
                    member_data[membership.id]['fed_in'] += fed_in
        
        # Calcola l'energia condivisa totale
        total_production = sum(data['produced'] for data in member_data.values())
        total_consumption = sum(data['consumed'] for data in member_data.values())
        total_self_consumed = sum(data['self_consumed'] for data in member_data.values())
        
        # L'energia condivisa è il minimo tra:
        # - energia prodotta e immessa in rete (produzione - autoconsumo)
        # - energia consumata e non autoprodotta (consumo - autoconsumo)
        production_surplus = total_production - total_self_consumed
        consumption_deficit = total_consumption - total_self_consumed
        shared_energy = min(production_surplus, consumption_deficit)
        
        if shared_energy <= 0:
            self.logger.info(f"Nessuna energia condivisa nel periodo {period_start.strftime('%Y-%m')}")
            return Decimal('0'), member_data
        
        # Calcola la quota di energia condivisa per ciascun membro
        total_producer_incentive = shared_energy * self.incentive_rate * self.producer_share
        total_consumer_incentive = shared_energy * self.incentive_rate * self.consumer_share
        total_grid_savings = shared_energy * self.grid_savings_rate
        
        # Calcola la proporzione di energia prodotta e consumata per ciascun membro
        total_fed_in = sum(data['fed_in'] for data in member_data.values())
        
        for member_id, data in member_data.items():
            # Calcola incentivi per i produttori in base alla proporzione di energia immessa
            if total_fed_in > 0 and data['fed_in'] > 0:
                producer_share = data['fed_in'] / total_fed_in
                data['incentive'] += total_producer_incentive * producer_share
            
            # Calcola incentivi per i consumatori in base alla proporzione dei consumi
            if total_consumption > 0 and data['consumed'] > total_self_consumed:
                consumption_share = (data['consumed'] - data['self_consumed']) / consumption_deficit
                data['incentive'] += total_consumer_incentive * consumption_share
                
                # Calcola risparmi di rete
                data['grid_savings'] = total_grid_savings * consumption_share
            
            # Assegna quota di energia condivisa
            if total_consumption > 0:
                data['shared'] = shared_energy * ((data['consumed'] - data['self_consumed']) / consumption_deficit)
        
        return shared_energy, member_data
    
    def _format_settlement_results(self, settlement):
        """
        Formatta i risultati del settlement in un dizionario
        
        Args:
            settlement: Oggetto CERSettlement
            
        Returns:
            dict: Risultati formattati
        """
        member_results = []
        for ms in settlement.member_settlements.all():
            member_results.append({
                'user': ms.membership.user.username,
                'produced': float(ms.produced),
                'consumed': float(ms.consumed),
                'shared': float(ms.shared),
                'self_consumed': float(ms.self_consumed),
                'fed_in': float(ms.fed_in),
                'incentive': float(ms.incentive_amount),
                'grid_savings': float(ms.grid_savings),
                'total_benefit': float(ms.total_benefit)
            })
        
        return {
            'id': settlement.id,
            'cer': settlement.cer.name,
            'period': settlement.period_name,
            'period_start': settlement.period_start.strftime('%Y-%m-%d'),
            'period_end': settlement.period_end.strftime('%Y-%m-%d'),
            'total_shared_energy': float(settlement.total_shared_energy),
            'total_incentive': float(settlement.total_incentive),
            'unit_incentive': float(settlement.unit_incentive),
            'status': settlement.status,
            'status_display': settlement.get_status_display(),
            'members': member_results
        }
    
    def get_settlement(self, settlement_id):
        """
        Ottiene i dati di un settlement esistente
        
        Args:
            settlement_id: ID del settlement
            
        Returns:
            dict: Dati di settlement formattati
        """
        try:
            settlement = CERSettlement.objects.get(id=settlement_id)
            return self._format_settlement_results(settlement)
        except CERSettlement.DoesNotExist:
            raise ValueError(f"Settlement con ID {settlement_id} non trovato")
    
    def finalize_settlement(self, settlement_id, user_id):
        """
        Finalizza un settlement cambiandone lo stato
        
        Args:
            settlement_id: ID del settlement
            user_id: ID dell'utente che approva
            
        Returns:
            dict: Dati di settlement aggiornati
        """
        try:
            with transaction.atomic():
                settlement = CERSettlement.objects.get(id=settlement_id)
                
                if settlement.status != 'DRAFT':
                    raise ValueError(f"Solo i settlement in bozza possono essere finalizzati. Stato attuale: {settlement.status}")
                
                settlement.status = 'FINALIZED'
                settlement.approved_by_id = user_id
                settlement.save()
                
                self.logger.info(f"Settlement {settlement_id} finalizzato da utente {user_id}")
                return self._format_settlement_results(settlement)
        except CERSettlement.DoesNotExist:
            raise ValueError(f"Settlement con ID {settlement_id} non trovato")
    
    def approve_settlement(self, settlement_id, user_id):
        """
        Approva un settlement finalizzato
        
        Args:
            settlement_id: ID del settlement
            user_id: ID dell'utente che approva
            
        Returns:
            dict: Dati di settlement aggiornati
        """
        try:
            with transaction.atomic():
                settlement = CERSettlement.objects.get(id=settlement_id)
                
                if settlement.status != 'FINALIZED':
                    raise ValueError(f"Solo i settlement finalizzati possono essere approvati. Stato attuale: {settlement.status}")
                
                settlement.status = 'APPROVED'
                settlement.approved_by_id = user_id
                settlement.save()
                
                self.logger.info(f"Settlement {settlement_id} approvato da utente {user_id}")
                return self._format_settlement_results(settlement)
        except CERSettlement.DoesNotExist:
            raise ValueError(f"Settlement con ID {settlement_id} non trovato")
    
    def distribute_settlement(self, settlement_id, user_id):
        """
        Imposta lo stato di un settlement come distribuito (benefici assegnati ai membri)
        
        Args:
            settlement_id: ID del settlement
            user_id: ID dell'utente che distribuisce
            
        Returns:
            dict: Dati di settlement aggiornati
        """
        try:
            with transaction.atomic():
                settlement = CERSettlement.objects.get(id=settlement_id)
                
                if settlement.status != 'APPROVED':
                    raise ValueError(f"Solo i settlement approvati possono essere distribuiti. Stato attuale: {settlement.status}")
                
                settlement.status = 'DISTRIBUTED'
                settlement.save()
                
                self.logger.info(f"Settlement {settlement_id} distribuito da utente {user_id}")
                return self._format_settlement_results(settlement)
        except CERSettlement.DoesNotExist:
            raise ValueError(f"Settlement con ID {settlement_id} non trovato")
    
    def get_member_settlements(self, user_id):
        """
        Ottiene tutti i settlement per un membro specifico
        
        Args:
            user_id: ID dell'utente membro
            
        Returns:
            list: Lista di settlement per il membro
        """
        member_settlements = MemberSettlement.objects.filter(
            membership__user_id=user_id
        ).select_related(
            'settlement', 'membership', 'membership__user'
        ).order_by('-settlement__period_start')
        
        results = []
        for ms in member_settlements:
            results.append({
                'settlement_id': ms.settlement.id,
                'cer': ms.settlement.cer.name,
                'period': ms.settlement.period_name,
                'status': ms.settlement.status,
                'status_display': ms.settlement.get_status_display(),
                'produced': float(ms.produced),
                'consumed': float(ms.consumed),
                'shared': float(ms.shared),
                'incentive': float(ms.incentive_amount),
                'grid_savings': float(ms.grid_savings),
                'total_benefit': float(ms.total_benefit)
            })
        
        return results