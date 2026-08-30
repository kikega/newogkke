"""
Vistas relacionadas con la gestión de cursillos
"""

# Python
import datetime
import json
import os

# Django
from django.core.exceptions import PermissionDenied

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.http import FileResponse
from django.urls import reverse_lazy

# App administracion
from administracion.models import Alumno, Cursillo, Examen

# Utilidades
from administracion.utils import enviar_correo_html

# Formularios
from administracion.forms import InscripcionAlumnosForm, CursoForm

class CursillosView(LoginRequiredMixin, ListView):
    """Listado de cursillos realizados"""

    template_name = 'administracion/cursillos.html'
    model = Cursillo
    context_object_name = 'cursillos'


    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()

        # Obtenemos la fecha actual
        hoy = datetime.date.today()
        context['hoy'] = hoy
        return context


class CursilloDetailView(LoginRequiredMixin, DetailView):
    """
    Obtenemos el detalle de cada cursillo
    Los alumnos que han asistido
    """

    model = Cursillo
    template_name = 'administracion/detalle_cursillo.html'
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_actual = self.get_object()

        # Obtenemos datos del usuario logado 
        user = self.request.user
        
        if not user.externo:
            # Obtenemos datos del alumno para ver si ya está inscrito
            try:
                alumno = Alumno.objects.select_related('usuario').get(usuario=user)
                alumno_cursillo = curso_actual.alumnos.filter(pk=alumno.id).exists()
                context['alumno_cursillo_inscrito'] = alumno_cursillo
            except Alumno.DoesNotExist:
                context['alumno_cursillo_inscrito'] = False

            # Obtenemos el dato si es instructor
            es_instructor = False
            if user.is_authenticated:
                es_instructor = user.groups.filter(name='Instructor').exists()
            # Añades la variable booleana al contexto
            context['usuario_es_instructor'] = es_instructor

        # Obtenemos todos los asistentes a un cursillo
        # asistentes_obj = Cursillo.objects.select_related('alumnos').get(pk=curso_actual.id)
        context["asistentes"] = curso_actual.alumnos.select_related('dojo').all().order_by('apellidos')
        # Obtenemos la fecha actual
        context['hoy'] = datetime.date.today()

        return context


class CursoNuevoView(LoginRequiredMixin, CreateView):
    """
    Creamos un curso nuevo
    """
    template_name = 'administracion/cursillos.html'
    model = Cursillo
    form_class = CursoForm
    success_url = reverse_lazy('administracion:cursillos')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("No tienes permiso para crear cursos.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cursillos'] = Cursillo.objects.all()
        context['cantidad'] = Cursillo.objects.count()
        return context


class CursilloExaminaListView(LoginRequiredMixin, DetailView):
    """
    Listado de todos los que se examinan en un cursillo
    """

    model = Cursillo
    template_name = 'administracion/cursillo_examinan.html'
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_actual = self.get_object()

        # Obtenemos todos los alumnos que se examinan en el cursillo
        context['examinan'] = Examen.objects.filter(evento=curso_actual).select_related('alumno').order_by('alumno__apellidos')
        context['curso'] = curso_actual
        context['hoy'] = datetime.date.today()

        return context


class CursilloEstadisticasView(LoginRequiredMixin, DetailView):
    """
    Obtiene las estadisticas de todos los cintos negros de cada Dojo que han asistido al cursillo
    """

    model = Cursillo
    template_name = "administracion/cursillo_estadisticas.html"
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        curso_actual = self.object
        context['curso'] = curso_actual

        asistentes_por_dojo = curso_actual.alumnos.values(
            'dojo__nombre'  # Agrupa por el nombre del Dojo
        ).annotate(
            total_asistentes=Count('id') # Cuenta los alumnos (id) en cada grupo de dojo
        ).order_by('-total_asistentes')
        context['estadisticas_asistentes_por_dojo'] = asistentes_por_dojo

        # Preparar datos para el gráfico
        labels_dojo = []
        values_asistentes = []

        for item in asistentes_por_dojo:
            labels_dojo.append(item['dojo__nombre'])
            values_asistentes.append(item['total_asistentes'])

        # Convertir a JSON para pasarlo a JavaScript en la plantilla
        context['asistentes_por_dojo'] = json.dumps({
            'labels': labels_dojo,
            'values': values_asistentes,
        })
        return context


class CursilloInscripcionAlumnoView(LoginRequiredMixin, View):
    """
    Inscripción o anulación directa de un alumno individual a un cursillo mediante petición POST.
    """
    def post(self, request, pk):
        cursillo = get_object_or_404(Cursillo, pk=pk)
        action = request.POST.get('action', 'inscribir')

        try:
            alumno = Alumno.objects.get(usuario=request.user)
        except Alumno.DoesNotExist:
            messages.error(request, "No tienes un perfil de alumno asociado para gestionar inscripciones.")
            return redirect('administracion:cursillo_detalle', pk=cursillo.id)

        if action == 'desinscribir':
            if cursillo.alumnos.filter(pk=alumno.id).exists():
                cursillo.alumnos.remove(alumno)
                messages.success(request, f"Has anulado correctamente tu inscripción en {cursillo.evento}.")
            else:
                messages.info(request, "No estabas inscrito en este cursillo.")
        else:
            if not cursillo.alumnos.filter(pk=alumno.id).exists():
                cursillo.alumnos.add(alumno)
                messages.success(request, f"Te has inscrito correctamente en {cursillo.evento}.")
            else:
                messages.info(request, "Ya estás inscrito en este cursillo.")

        return redirect('administracion:cursillo_detalle', pk=cursillo.id)


class CursilloInscripcionInstructorView(LoginRequiredMixin, TemplateView):
    """
    Inscripción masiva de alumnos por parte del instructor de su dojo o administradores.
    """
    template_name = 'administracion/inscripcion_instructor.html'
    cursillo = None

    def dispatch(self, request, *args, **kwargs):
        self.cursillo = get_object_or_404(Cursillo, pk=self.kwargs['pk'])
        user = request.user

        # Verificar permisos: debe ser staff o instructor
        es_instructor = False
        if user.is_authenticated:
            try:
                alumno = Alumno.objects.get(usuario=user)
                es_instructor = alumno.instructor
            except Alumno.DoesNotExist:
                pass

        if not (user.is_staff or user.is_superuser or es_instructor):
            raise PermissionDenied("No tienes permiso para gestionar la lista de inscritos de este cursillo.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepara el contexto para la plantilla, incluyendo el formulario.
        """
        context = super().get_context_data(**kwargs)
        context['cursillo'] = self.cursillo
        context['form'] = InscripcionAlumnosForm(
            user=self.request.user,
            cursillo=self.cursillo
        )
        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de inscripción de alumnos del dojo de forma atómica.
        """
        form = InscripcionAlumnosForm(
            request.POST, 
            user=request.user,
            cursillo=self.cursillo
        )

        if form.is_valid():
            alumnos_a_inscribir = form.cleaned_data['alumnos']

            try:
                instructor = Alumno.objects.get(usuario=request.user)
                dojo = instructor.dojo
                # Obtenemos los alumnos del dojo del instructor
                alumnos_dojo_pks = set(Alumno.objects.filter(dojo=dojo, instructor=False, activo=True).values_list('pk', flat=True))
                selected_dojo_pks = set(alumnos_a_inscribir.values_list('pk', flat=True)) & alumnos_dojo_pks

                # Obtenemos los que estaban inscritos previamente de este dojo
                actuales_dojo_pks = set(self.cursillo.alumnos.filter(dojo=dojo).values_list('pk', flat=True))

                to_remove = actuales_dojo_pks - selected_dojo_pks
                to_add = selected_dojo_pks - actuales_dojo_pks

                if to_remove:
                    self.cursillo.alumnos.remove(*to_remove)
                if to_add:
                    self.cursillo.alumnos.add(*to_add)

            except Alumno.DoesNotExist:
                # Administrador global sin perfil de alumno
                self.cursillo.alumnos.set(alumnos_a_inscribir)

            messages.success(request, f"Se han actualizado las inscripciones correctamente.")
        else:
            messages.error(request, "Hubo un error con el formulario. Por favor, inténtalo de nuevo.")
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)
        
        return redirect("administracion:cursillo_detalle", pk=self.cursillo.id)


@login_required
def descargar_circular(request, pk):
    """
    Descarga segura de la circular en PDF asociada al cursillo.
    """
    cursillo = get_object_or_404(Cursillo, pk=pk)

    if cursillo.circular and hasattr(cursillo.circular, 'path'):
        circular_path = cursillo.circular.path
        if os.path.exists(circular_path):
            filename = os.path.basename(cursillo.circular.name)
            response = FileResponse(open(circular_path, 'rb'), as_attachment=True, filename=filename)
            if not settings.DEBUG:
                response['Connection'] = 'close'
            return response
        
    return redirect("administracion:errores", error_code=404)
