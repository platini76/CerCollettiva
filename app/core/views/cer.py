# core/views/cer.py
import logging
from django.views.generic import ListView, DetailView, CreateView, FormView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .base import BaseCERView
from ..models import CERConfiguration, CERMembership, Plant, PlantMeasurement
from ..forms import CERConfigurationForm, CERMembershipForm
from .mixins.gdpr import GDPRConsentRequiredMixin

logger = logging.getLogger(__name__)

class CERListView(LoginRequiredMixin, ListView):
    """Lista delle CER"""
    model = CERConfiguration
    template_name = 'core/cer_list.html'
    context_object_name = 'available_cers'
    
    def get_queryset(self):
        # Query base semplice
        queryset = CERConfiguration.objects.filter(is_active=True)
        #print(f"1. CER attive trovate: {queryset.count()}")
        
        # Aggiunge il conteggio dei membri
        queryset = queryset.annotate(
            members_count=Count('members', distinct=True)
        )
        #print(f"2. Query finale: {queryset.query}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Info per il bottone "Aderisci"
        context['user_memberships'] = user.cer_memberships.filter(
            is_active=True
        ).select_related('cer_configuration')
        
        # Debug info
        context.update({
            'debug': {
                'total_cers': CERConfiguration.objects.count(),
                'active_cers': CERConfiguration.objects.filter(is_active=True).count(),
                'username': user.username,
                'is_staff': user.is_staff,
                'user_memberships_count': user.cer_memberships.filter(
                    is_active=True
                ).count()
            }
        })
        
        return context
class CERDetailView(BaseCERView):
    """Dettaglio di una CER"""
    template_name = 'core/cer_detail.html'
    context_object_name = 'cer'
    
    def dispatch(self, request, *args, **kwargs):
        # Verifica che l'ID della CER sia valido prima di procedere
        try:
            # Assicurati che kwargs['pk'] esista e sia un valore valido
            if 'pk' not in kwargs or not kwargs['pk']:
                logger.error("Missing pk parameter in CERDetailView")
                messages.error(request, _("Identificativo CER mancante"))
                return redirect('core:cer_list')
            
            self.get_object()
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            # Log dell'errore e redirect alla lista delle CER
            logger.error(f"Error in CERDetailView: {str(e)}")
            messages.error(request, _("CER non trovata o accesso non autorizzato"))
            return redirect('core:cer_list')
    
    def get_object(self):
        """Recupera l'oggetto CER"""
        return get_object_or_404(
            CERConfiguration,
            pk=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cer = self.get_object()
        
        # Recupera membership dell'utente
        user_membership = None
        if not self.request.user.is_staff:
            try:
                user_membership = CERMembership.objects.get(
                    user=self.request.user,
                    cer_configuration=cer,
                    is_active=True
                )
            except CERMembership.DoesNotExist:
                # L'utente non è un membro attivo di questa CER
                pass
        
        # Calcola statistiche energetiche
        time_threshold = self.get_time_threshold()
        energy_stats = self._calculate_cer_energy_stats(cer, time_threshold)
        
        context.update({
            'user_membership': user_membership,
            'energy_stats': energy_stats,
            'members': cer.memberships.filter(is_active=True).select_related('user'),
            'plants': self._get_filtered_plants(cer),
            'is_admin': self.request.user.is_staff or 
                       (user_membership and user_membership.role == 'ADMIN')
        })
        return context
        
    def _calculate_cer_energy_stats(self, cer, time_threshold):
        """Calcola le statistiche energetiche della CER"""
        try:
            # Usa PlantMeasurement con il campo corretto 'value'
            measurements = PlantMeasurement.objects.select_related(
                'plant'
            ).filter(
                plant__cer_configuration=cer,
                timestamp__gte=time_threshold
            )
            
            # Calcola totale produzione
            producer_total = measurements.filter(
                plant__plant_type='PRODUCER'
            ).aggregate(
                total=Sum('value')  # Usa 'value' invece di 'power'
            )['total'] or 0
            
            # Calcola totale consumo
            consumer_total = measurements.filter(
                plant__plant_type='CONSUMER'
            ).aggregate(
                total=Sum('value')  # Usa 'value' invece di 'power'
            )['total'] or 0
            
            # Ritorna le statistiche complete
            return {
                'total_production': producer_total,
                'total_consumption': abs(consumer_total),
                'net_energy': producer_total - abs(consumer_total),
                'measurement_period': {
                    'start': time_threshold,
                    'end': timezone.now()
                }
            }
            
        except Exception as e:
            logger.error(f"Errore nel calcolo delle statistiche energetiche: {str(e)}")
            return {
                'total_production': 0,
                'total_consumption': 0,
                'net_energy': 0,
                'measurement_period': {
                    'start': time_threshold,
                    'end': timezone.now()
                }
            }
    
    def _get_filtered_plants(self, cer):
        """Recupera gli impianti filtrati in base ai permessi"""
        plants = cer.plants.filter(is_active=True)
        if not self.request.user.is_staff:
            plants = plants.filter(owner=self.request.user)
        return plants.select_related('owner')

class CERJoinView(BaseCERView, GDPRConsentRequiredMixin):
    """Vista per l'adesione a una CER"""
    template_name = 'core/cer_join.html'
    form_class = CERMembershipForm
    
    def get_object(self):
        return get_object_or_404(
            CERConfiguration,
            pk=self.kwargs['pk'],
            is_active=True
        )
    
    def dispatch(self, request, *args, **kwargs):
        cer = self.get_object()
        
        # Verifica se l'utente è già membro
        if CERMembership.objects.filter(
            user=request.user,
            cer_configuration=cer
        ).exists():
            messages.warning(request, _("Sei già membro di questa CER"))
            return redirect('core:cer_detail', pk=cer.pk)
            
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        membership = form.save(commit=False)
        membership.user = self.request.user
        membership.cer_configuration = self.get_object()
        membership.save()
        
        messages.success(self.request, _("Richiesta di adesione inviata con successo"))
        return redirect('core:cer_detail', pk=self.get_object().pk)

class CERCreateView(FormView, BaseCERView, UserPassesTestMixin):
    """Vista per la creazione di una nuova CER"""
    template_name = 'core/cer_form.html'
    form_class = CERConfigurationForm
    success_url = '/cer/'  # Fallback, verrà sovrascritto in form_valid
    
    def test_func(self):
        """Solo gli amministratori possono creare CER"""
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crea Nuova CER'
        return context
    
    def form_valid(self, form):
        """Salva il form e reindirizza"""
        cer = form.save()
        messages.success(self.request, _("Comunità energetica creata con successo"))
        return redirect('core:cer_detail', pk=cer.pk)
        
class CERDistributionSettingsView(FormView, BaseCERView, UserPassesTestMixin):
    """Vista per la gestione delle regole di ripartizione degli incentivi per una CER"""
    template_name = 'core/cer_distribution_settings.html'
    
    # Rimuovi success_url statico e usa get_success_url invece
    def get_success_url(self):
        """Genera l'URL di successo in modo dinamico"""
        pk = self.kwargs.get('pk')
        if pk:
            return reverse('core:cer_detail', kwargs={'pk': pk})
        else:
            logger.warning("Missing pk in get_success_url for CERDistributionSettingsView")
            return reverse('core:cer_list')
    
    def dispatch(self, request, *args, **kwargs):
        # Verifica che l'ID della CER sia valido prima di procedere
        try:
            # Verifica che pk esista e sia un valore valido
            if 'pk' not in kwargs or not kwargs['pk']:
                logger.error("Missing pk parameter in CERDistributionSettingsView")
                messages.error(request, _("Identificativo CER mancante"))
                return redirect('core:cer_list')
            
            self.get_object()
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            # Log dell'errore e redirect alla lista delle CER
            logger.error(f"Error in CERDistributionSettingsView: {str(e)}")
            messages.error(request, _("CER non trovata o accesso non autorizzato"))
            return redirect('core:cer_list')
    
    def get_context_data(self, **kwargs):
        """Prepara i dati di contesto per la vista"""
        context = super().get_context_data(**kwargs)
        context['cer'] = self.get_object()
        return context
    
    def test_func(self):
        """Verifica se l'utente può accedere alla pagina"""
        if self.request.user.is_staff:
            return True
            
        cer = self.get_object()
        return CERMembership.objects.filter(
            user=self.request.user,
            cer_configuration=cer,
            role='ADMIN',
            is_active=True
        ).exists()
    
    def get_object(self):
        """Recupera l'oggetto CER"""
        return get_object_or_404(
            CERConfiguration,
            pk=self.kwargs['pk']
        )
    
    def get_form(self):
        """Crea form specifico per le impostazioni di distribuzione"""
        from django.forms import modelform_factory
        DistributionForm = modelform_factory(
            CERConfiguration, 
            fields=['producer_share', 'consumer_share', 'admin_share', 
                   'investment_fund_share', 'solidarity_fund_share', 'legal_fund_share',
                   'accountant_fund_share', 'incentive_rate', 'grid_savings_rate']
        )
        
        try:
            cer = self.get_object()
            if self.request.method == 'POST':
                return DistributionForm(self.request.POST, instance=cer)
            else:
                return DistributionForm(instance=cer)
        except:
            # Fallback in caso di errore
            return DistributionForm()
    
    def get_context_data(self, **kwargs):
        """Prepara i dati di contesto per la vista"""
        context = super().get_context_data(**kwargs)
        cer = self.get_object()
        form = self.get_form()
        
        from decimal import Decimal
        
        # Calcola valori di esempio per mostrare gli effetti
        example_energy = Decimal('1000.00')  # 1000 kWh
        producer_amount = (example_energy * cer.incentive_rate * (cer.producer_share / Decimal('100.0'))).quantize(Decimal('0.01'))
        consumer_amount = (example_energy * cer.incentive_rate * (cer.consumer_share / Decimal('100.0'))).quantize(Decimal('0.01'))
        grid_savings = (example_energy * cer.grid_savings_rate).quantize(Decimal('0.01'))
        total_incentive = (example_energy * cer.incentive_rate).quantize(Decimal('0.01'))
        
        context.update({
            'cer': cer,
            'form': form,
            'example_energy': example_energy,
            'producer_amount': producer_amount,
            'consumer_amount': consumer_amount,
            'grid_savings': grid_savings,
            'total_incentive': total_incentive
        })
        
        return context
    
    def form_valid(self, form):
        """Salva il form validato"""
        try:
            cer = form.save()
            messages.success(self.request, _("Regole di ripartizione aggiornate con successo"))
            # Usa reverse per costruire l'URL completo con il pk corretto
            success_url = reverse('core:cer_detail', kwargs={'pk': cer.pk})
            return redirect(success_url)
        except Exception as e:
            logger.error(f"Error saving distribution settings: {str(e)}")
            messages.error(self.request, _("Errore nel salvataggio: {}").format(str(e)))
            return self.form_invalid(form)