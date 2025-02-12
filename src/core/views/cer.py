# core/views/cer.py
import logging
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
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
            user_membership = get_object_or_404(
                CERMembership,
                user=self.request.user,
                cer_configuration=cer,
                is_active=True
            )
        
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