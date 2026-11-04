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
    queryset = MiembroDirectiva.objects.filter(activo=True).select_related('cargo', 'alumno', 'alumno__dojo', 'usuario').order_by('cargo__orden_jerarquico', 'orden')

    def get_context_data(self, **kwargs):
        # Llamamos a la implementación base para obtener el contexto estándar
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        # Separamos la lógica jerárquica dentro del contexto
        # 1. Buscamos al cargo con menor orden (asumimos que es el Presidente)
        presidente = qs.first()
        context['presidente'] = presidente
        
        # 2. Miembros de la ejecutiva (excluyendo al presidente)
        context['ejecutiva'] = qs.exclude(id=presidente.id) if presidente else qs
        
        return context
    