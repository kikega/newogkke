"""
Vistas relacionadas con la gestión de los dojos
"""

# Python
import json

# Django
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Count

# App administracion
from administracion.models import Alumno, Dojo, Peticion, Tablon, obtener_tablon_intercalado
from administracion.permissions import InstructorOrStaffRequiredMixin, obtener_alumno_instructor
from administracion.views.dojo_portal import usuario_puede_gestionar_dojo

# Formularios
from administracion.forms import DojoPortalConfigForm, TablonNuevoForm

class DojosView(InstructorOrStaffRequiredMixin, ListView):
    """Listado de gimnasios de la asociación (Solo Usuarios Globales)"""

    template_name = 'administracion/dojos.html'
    model = Dojo
    context_object_name = 'dojos'


    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()
        return context


class DojoDetailView(InstructorOrStaffRequiredMixin, DetailView):
    """
    Detalle de un Dojo en el Core Nacional (Solo Usuarios Globales)
    """

    template_name = 'administracion/detalle_dojo.html'
    model = Dojo
    context_object_name = 'dojo'

    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        # Obtenemos el objeto dojo actual
        dojo_actual = self.get_object()
        # Obtenemos los datos del instructor y lo añadimos al contexto
        instructor_obj = Alumno.objects.select_related('usuario').filter(
            dojo=dojo_actual,
            instructor=True
        ).first()
        context['instructor'] = instructor_obj

        # Obtenemos datos del usuario logado para añadirlo al contexto
        user = self.request.user
        es_instructor = obtener_alumno_instructor(user) is not None
        context['usuario_es_instructor'] = es_instructor

        # Obtenemos todos los cintos negros del dojo
        cintos_negros_dojo_obj = Alumno.objects.filter(dojo = dojo_actual, instructor=False).order_by("apellidos")
        context['cintos_negros_dojo'] = cintos_negros_dojo_obj

        # Obtenemos los cintos negros por grado
        # 1. Filtra por el dojo actual y que no sean instructores
        # 2. Agrupa por 'grado' usando values('grado')
        # 3. Cuenta los alumnos en cada grupo ('grado')
        # 4. Ordena por 'grado'
        cintos_negros_por_grado = Alumno.objects.filter(
            dojo=dojo_actual,
            instructor=False
        ).values('grado').annotate(
            total=Count('id')
        ).order_by('grado')
        # Extracción de Datos
        labels = [f"{item['grado']}º DAN" for item in cintos_negros_por_grado]
        values = [item['total'] for item in cintos_negros_por_grado]
        context['cinturon_negro_data_json'] = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': f'Alumnos por Grado en {dojo_actual.nombre}', # Título dinámico
        })
        context['total_cintos_negros'] = sum(values)

        # Obtenemos las peticiones pendientes y anuncios del tablón por dojo
        peticiones = Peticion.objects.for_dojo(dojo_actual).filter(finalizada=False)
        numero_peticiones = peticiones.count()
        puede_gestionar_dojo = usuario_puede_gestionar_dojo(user, dojo_actual)
        tablon_particulares_qs = Tablon.objects.for_dojo(dojo_actual)
        tablon_intercalado = obtener_tablon_intercalado(tablon_particulares_qs)
        context['peticiones'] = peticiones
        context['numero_peticiones'] = numero_peticiones
        context['tablon'] = tablon_intercalado
        context['numero_anuncios_tablon'] = len(tablon_intercalado)
        context['numero_anuncios_particulares_tablon'] = tablon_particulares_qs.count()
        context["form"] = TablonNuevoForm()
        context["puede_gestionar_dojo"] = puede_gestionar_dojo
        context["config_form"] = DojoPortalConfigForm(instance=dojo_actual) if puede_gestionar_dojo else None
        context["dojo_base_domain"] = getattr(settings, "DOJO_BASE_DOMAIN", "ogkke.es")

        return context

