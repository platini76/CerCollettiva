# energy/views/settlement_views.py
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from core.models import CERConfiguration, CERMembership, Plant
from ..models.energy import CERSettlement, MemberSettlement
from ..services.energy_calculator_settlement import CERSettlementCalculator
import logging
import json
from decimal import Decimal

logger = logging.getLogger(__name__)

@login_required
def settlement_dashboard(request):
    """
    Vista per la dashboard dei settlements CER
    Mostra i settlements disponibili per l'utente
    """
    user = request.user
    
    # Se l'utente è staff, mostra tutti i settlements
    if user.is_staff:
        settlements = CERSettlement.objects.all().order_by('-period_start')
        memberships = CERMembership.objects.filter(is_active=True)
    else:
        # Altrimenti mostra solo i settlements per le CER di cui è membro
        memberships = CERMembership.objects.filter(user=user, is_active=True)
        settlements = CERSettlement.objects.filter(cer__in=[m.cer for m in memberships]).order_by('-period_start')
    
    return render(request, 'energy/settlements/dashboard.html', {
        'settlements': settlements,
        'memberships': memberships
    })

@login_required
def settlement_detail(request, settlement_id):
    """
    Vista per il dettaglio di un settlement
    Mostra i dettagli di un settlement specifico
    """
    user = request.user
    
    # Verifica l'accesso
    settlement = get_object_or_404(CERSettlement, id=settlement_id)
    
    if not user.is_staff:
        # Verifica che l'utente sia membro della CER
        membership = CERMembership.objects.filter(user=user, cer=settlement.cer, is_active=True).first()
        if not membership:
            messages.error(request, "Non hai accesso a questo settlement")
            return redirect('energy:settlements')
    
    # Ottieni i dettagli del settlement
    calculator = CERSettlementCalculator()
    settlement_data = calculator.get_settlement(settlement_id)
    
    return render(request, 'energy/settlements/detail.html', {
        'settlement': settlement,
        'settlement_data': settlement_data
    })

@staff_member_required
def settlement_new(request):
    """
    Vista per la creazione di un nuovo settlement
    Form per selezionare CER e periodo
    """
    cers = CERConfiguration.objects.all()
    
    # Calcola opzioni di periodo (mesi degli ultimi 2 anni)
    periods = []
    now = timezone.now()
    for i in range(24):
        dt = now.replace(day=1) - timedelta(days=30*i)
        periods.append({
            'value': dt.strftime('%Y-%m'),
            'label': dt.strftime('%B %Y')
        })
    
    return render(request, 'energy/settlements/new.html', {
        'cers': cers,
        'periods': periods
    })

@staff_member_required
@require_http_methods(["POST"])
def settlement_create(request):
    """
    Vista per la creazione effettiva di un settlement
    Elabora il form e crea un nuovo settlement
    """
    cer_id = request.POST.get('cer')
    period = request.POST.get('period')
    
    if not cer_id or not period:
        messages.error(request, "CER e periodo sono richiesti")
        return redirect('energy:settlement_new')
    
    try:
        # Parsing del periodo
        year, month = map(int, period.split('-'))
        
        # Calcola il settlement
        calculator = CERSettlementCalculator()
        settlement_data = calculator.calculate_monthly_settlement(
            year=year,
            month=month,
            cer_id=cer_id,
            user_id=request.user.id
        )
        
        messages.success(request, f"Settlement creato con successo: {settlement_data['period']}")
        return redirect('energy:settlement_detail', settlement_id=settlement_data['id'])
    except Exception as e:
        logger.exception("Errore nella creazione del settlement")
        messages.error(request, f"Errore nella creazione del settlement: {str(e)}")
        return redirect('energy:settlement_new')

@staff_member_required
@require_http_methods(["POST"])
def settlement_action(request, settlement_id):
    """
    Vista per le azioni sul settlement (finalizza, approva, distribuisci)
    """
    action = request.POST.get('action')
    
    if not action:
        messages.error(request, "Azione non specificata")
        return redirect('energy:settlement_detail', settlement_id=settlement_id)
    
    try:
        calculator = CERSettlementCalculator()
        
        if action == 'finalize':
            settlement_data = calculator.finalize_settlement(settlement_id, request.user.id)
            messages.success(request, "Settlement finalizzato con successo")
        elif action == 'approve':
            settlement_data = calculator.approve_settlement(settlement_id, request.user.id)
            messages.success(request, "Settlement approvato con successo")
        elif action == 'distribute':
            settlement_data = calculator.distribute_settlement(settlement_id, request.user.id)
            messages.success(request, "Settlement distribuito con successo")
        else:
            messages.error(request, f"Azione {action} non supportata")
        
        return redirect('energy:settlement_detail', settlement_id=settlement_id)
    except Exception as e:
        logger.exception(f"Errore nell'esecuzione dell'azione {action}")
        messages.error(request, f"Errore: {str(e)}")
        return redirect('energy:settlement_detail', settlement_id=settlement_id)

@login_required
def settlement_member_view(request):
    """
    Vista per i membri per visualizzare i propri settlements
    """
    user = request.user
    
    # Ottieni i settlements del membro
    calculator = CERSettlementCalculator()
    member_settlements = calculator.get_member_settlements(user.id)
    
    # Ottieni le membership attive dell'utente
    memberships = CERMembership.objects.filter(user=user, is_active=True)
    
    return render(request, 'energy/settlements/member.html', {
        'member_settlements': member_settlements,
        'memberships': memberships
    })

# API VIEWS
@login_required
def api_settlement_list(request):
    """
    API per ottenere la lista dei settlements
    """
    user = request.user
    
    try:
        # Se l'utente è staff, mostra tutti i settlements
        if user.is_staff:
            settlements = CERSettlement.objects.all().order_by('-period_start')
        else:
            # Altrimenti mostra solo i settlements per le CER di cui è membro
            memberships = CERMembership.objects.filter(user=user, is_active=True)
            settlements = CERSettlement.objects.filter(cer__in=[m.cer for m in memberships]).order_by('-period_start')
        
        results = []
        for settlement in settlements:
            results.append({
                'id': settlement.id,
                'cer': settlement.cer.name,
                'period': settlement.period_name,
                'month': settlement.period_start.strftime('%B'),
                'year': settlement.period_start.year,
                'total_shared_energy': float(settlement.total_shared_energy),
                'total_incentive': float(settlement.total_incentive),
                'status': settlement.status,
                'status_display': settlement.get_status_display(),
                'created_at': settlement.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'settlements': results
        })
    except Exception as e:
        logger.exception("Errore nell'API settlements")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_settlement_detail(request, settlement_id):
    """
    API per ottenere i dettagli di un settlement
    """
    user = request.user
    
    try:
        settlement = get_object_or_404(CERSettlement, id=settlement_id)
        
        # Verifica accesso
        if not user.is_staff:
            membership = CERMembership.objects.filter(user=user, cer=settlement.cer, is_active=True).first()
            if not membership:
                return JsonResponse({
                    'success': False,
                    'error': "Non hai accesso a questo settlement"
                }, status=403)
        
        # Ottieni i dettagli
        calculator = CERSettlementCalculator()
        settlement_data = calculator.get_settlement(settlement_id)
        
        return JsonResponse({
            'success': True,
            'settlement': settlement_data
        })
    except Exception as e:
        logger.exception(f"Errore nell'API settlement detail {settlement_id}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_member_settlements(request):
    """
    API per ottenere i settlements di un membro
    """
    user = request.user
    
    try:
        calculator = CERSettlementCalculator()
        member_settlements = calculator.get_member_settlements(user.id)
        
        return JsonResponse({
            'success': True,
            'settlements': member_settlements
        })
    except Exception as e:
        logger.exception("Errore nell'API member settlements")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_dashboard_summary(request):
    """
    API per ottenere i dati di riepilogo per la dashboard energetica
    Fornisce dati di produzione, consumo, condivisione e benefici economici
    Usato per popolare grafici e tabelle nella dashboard principale
    """
    user = request.user
    
    try:
        # Genera dati di mockup per i benefici economici
        # Questi saranno sostituiti con dati reali quando saranno disponibili i dati di settlement
        
        # Calcola periodo (ultimi 6 mesi)
        now = timezone.now()
        months = []
        for i in range(6):
            dt = now.replace(day=1) - timedelta(days=30*i)
            months.append(dt.strftime('%B %Y'))
        
        # Dati di mockup
        settlement_data = []
        
        # Se l'utente è admin, mostra dati aggregati per tutte le CER
        if user.is_staff:
            settlements = CERSettlement.objects.all().order_by('-period_start')[:6]
            if settlements:
                for settlement in settlements:
                    settlement_data.append({
                        'month': settlement.period_start.strftime('%B %Y'),
                        'produced': float(settlement.total_shared_energy) * 2,  # Approssimazione
                        'consumed': float(settlement.total_shared_energy) * 1.8,  # Approssimazione
                        'shared': float(settlement.total_shared_energy),
                        'benefit': float(settlement.total_incentive)
                    })
            else:
                # Dati di mockup se non ci sono settlements
                for i, month in enumerate(months):
                    factor = (6 - i) / 6  # Fattore decrescente per simulare crescita
                    settlement_data.append({
                        'month': month,
                        'produced': 1200 * factor,
                        'consumed': 980 * factor,
                        'shared': 680 * factor,
                        'benefit': 150 * factor
                    })
        else:
            # Per utenti normali, mostra solo i propri dati
            calculator = CERSettlementCalculator()
            member_settlements = calculator.get_member_settlements(user.id)
            
            if member_settlements:
                for ms in member_settlements[:6]:
                    settlement_data.append({
                        'month': ms['period'],
                        'produced': ms['produced'],
                        'consumed': ms['consumed'],
                        'shared': ms['shared'],
                        'benefit': ms['total_benefit']
                    })
            else:
                # Dati di mockup se non ci sono settlements
                for i, month in enumerate(months):
                    factor = (6 - i) / 6  # Fattore decrescente per simulare crescita
                    settlement_data.append({
                        'month': month,
                        'produced': 450 * factor,
                        'consumed': 380 * factor,
                        'shared': 250 * factor,
                        'benefit': 60 * factor
                    })
        
        # Calcola il consumo energetico
        # In futuro questi dati verranno presi dai dati reali
        consumption_data = {
            'produced': 0,
            'consumed': 0,
            'shared': 0,
            'fed_in': 0
        }
        
        # Calcola totali dai dati di settlement
        for data in settlement_data:
            consumption_data['produced'] += data['produced']
            consumption_data['consumed'] += data['consumed']
            consumption_data['shared'] += data['shared']
            consumption_data['fed_in'] += max(0, data['produced'] - data['consumed'])
        
        return JsonResponse({
            'success': True,
            'settlements': settlement_data,
            'consumption': consumption_data
        })
    except Exception as e:
        logger.exception("Errore nell'API dashboard summary")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'settlements': [],
            'consumption': {'produced': 0, 'consumed': 0, 'shared': 0, 'fed_in': 0}
        }, status=500)