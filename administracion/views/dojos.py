"""
Vistas relacionadas con la gestión de los dojos
"""

# Python
import json

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Count

# App administracion
from administracion.models import Alumno, Dojo, Peticion

# Formularios
from administracion.forms import  TablonNuevoForm

class DojosView(LoginRequiredMixin, ListView):
    """Listado de gimnasios de la asociación"""

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


class DojoDetailView(LoginRequiredMixin, DetailView):
    """
    Detalle de un Dojo
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
        print(f"Usuario: {user}")
        # Obtenemos el dato si es instructor
        es_instructor = False
        if user.is_authenticated:
            es_instructor = user.groups.filter(name='Instructor').exists()
            print(f"Usuario: {user}, es_instructor: {es_instructor}")
        # Añades la variable booleana al contexto
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

        # Obtenemos las peticiones pendientes por dojo
        peticiones = Peticion.objects.filter(dojo=dojo_actual, finalizada=False)
        numero_peticiones = peticiones.count()
        context['peticiones'] = peticiones
        context['numero_peticiones'] = numero_peticiones
        context["form"] = TablonNuevoForm()

        return context

