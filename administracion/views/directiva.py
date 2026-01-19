"""
    Vistas relacionadas con la gestión del equipo directivo
"""

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView

# App administracion
from administracion.models import MiembroDirectiva

class DirectivaView(LoginRequiredMixin, ListView):
    """Vista del equipo directivo"""
    model = MiembroDirectiva
    template_name = 'administracion/organigrama.html'
    # Definimos el queryset base: solo activos y optimizamos consultas con select_related
    queryset = MiembroDirectiva.objects.filter().select_related('cargo', 'alumno', 'usuario')

    def get_context_data(self, **kwargs):
        # Llamamos a la implementación base para obtener el contexto estándar
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        # Separamos la lógica jerárquica dentro del contexto
        # 1. Buscamos al cargo con menor orden (asumimos que es el Presidente)
        context['presidente'] = qs.order_by('cargo__orden_jerarquico').first()
        
        # 2. Miembros de la ejecutiva (excluyendo al presidente)
        context['ejecutiva'] = qs.filter().exclude(id=context['presidente'].id if context['presidente'] else None)
        
        return context
    