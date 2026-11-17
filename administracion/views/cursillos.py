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
from administracion.models import Alumno, AlumnoColor, Cursillo, Examen
from administracion.permissions import (
    InstructorOrStaffRequiredMixin,
    obtener_alumno_instructor,
    obtener_perfiles_alumno,
)

# Utilidades
from administracion.utils import enviar_correo_html

# Formularios
from administracion.forms import InscripcionAlumnosForm, CursoForm

class CursillosView(InstructorOrStaffRequiredMixin, ListView):
    """Listado general de cursillos realizados (Usuarios Globales)"""

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
        context['form'] = CursoForm()
        return context


def _resolver_estado_inscripcion_usuario(user, cursillo):
    """
    Devuelve (inscrito, puede_inscribirse) para el usuario autenticado en un cursillo,
    contemplando tanto Cinturones Negros (Alumno) como Cinturones de Color (AlumnoColor).
    """
    if not user or not user.is_authenticated or getattr(user, 'externo', False):
        return False, False
    alumno_dan, alumno_color = obtener_perfiles_alumno(user)
    if alumno_dan:
        return cursillo.alumnos.filter(pk=alumno_dan.pk).exists(), True
    if alumno_color:
        inscrito = cursillo.alumnos_color.filter(pk=alumno_color.pk).exists()
        return inscrito, bool(cursillo.abierto_cintos_color)
    return False, False


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
            inscrito, puede_inscribirse = _resolver_estado_inscripcion_usuario(user, curso_actual)
            context['alumno_cursillo_inscrito'] = inscrito
            context['puede_inscribirse_cursillo'] = puede_inscribirse
            context['usuario_es_instructor'] = obtener_alumno_instructor(user) is not None

        # Obtenemos todos los asistentes a un cursillo
        context["asistentes"] = curso_actual.alumnos.select_related('dojo').all().order_by('apellidos')
        context["asistentes_color"] = (
            curso_actual.alumnos_color.for_user(user)
            .select_related('dojo', 'grado_actual')
            .order_by('apellidos')
        )
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
        user = self.request.user

        if not user.externo:
            inscrito, puede_inscribirse = _resolver_estado_inscripcion_usuario(user, curso_actual)
            context['alumno_cursillo_inscrito'] = inscrito
            context['puede_inscribirse_cursillo'] = puede_inscribirse

        # Obtenemos todos los alumnos que se examinan en el cursillo
        context['examinan'] = Examen.objects.filter(evento=curso_actual).select_related('alumno', 'alumno__dojo').order_by('alumno__apellidos')
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
        context['hoy'] = datetime.date.today()

        user = self.request.user
        if not user.externo:
            inscrito, puede_inscribirse = _resolver_estado_inscripcion_usuario(user, curso_actual)
            context['alumno_cursillo_inscrito'] = inscrito
            context['puede_inscribirse_cursillo'] = puede_inscribirse

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
    Inscripción o anulación directa de un alumno individual (Cinto Negro o Cinto de Color mayor de edad)
    a un cursillo mediante petición POST. No envía correo al instructor; queda reflejado en la lista de inscritos.
    """
    def post(self, request, pk):
        cursillo = get_object_or_404(Cursillo, pk=pk)
        action = request.POST.get('action', 'inscribir')
        next_url = request.POST.get('next', '')

        def _redirect_target():
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('administracion:cursillo_detalle', pk=cursillo.id)

        alumno_dan, alumno_color = obtener_perfiles_alumno(request.user)

        if alumno_dan:
            if action == 'desinscribir':
                if cursillo.alumnos.filter(pk=alumno_dan.id).exists():
                    cursillo.alumnos.remove(alumno_dan)
                    messages.success(request, f"Has anulado correctamente tu inscripción en {cursillo.evento}.")
                else:
                    messages.info(request, "No estabas inscrito en este cursillo.")
            else:
                if not cursillo.alumnos.filter(pk=alumno_dan.id).exists():
                    cursillo.alumnos.add(alumno_dan)
                    messages.success(request, f"Te has inscrito correctamente en {cursillo.evento}.")
                else:
                    messages.info(request, "Ya estás inscrito en este cursillo.")
            return _redirect_target()

        if alumno_color:
            if action == 'desinscribir':
                if cursillo.alumnos_color.filter(pk=alumno_color.id).exists():
                    cursillo.alumnos_color.remove(alumno_color)
                    messages.success(request, f"Has anulado correctamente tu inscripción en {cursillo.evento}.")
                else:
                    messages.info(request, "No estabas inscrito en este cursillo.")
            else:
                if not cursillo.abierto_cintos_color:
                    messages.error(request, "Este cursillo está reservado exclusivamente para Cinturones Negros (DAN).")
                    return _redirect_target()
                if not cursillo.alumnos_color.filter(pk=alumno_color.id).exists():
                    cursillo.alumnos_color.add(alumno_color)
                    messages.success(request, f"Te has inscrito correctamente en {cursillo.evento}.")
                else:
                    messages.info(request, "Ya estás inscrito en este cursillo.")
            return _redirect_target()

        messages.error(request, "No tienes un perfil de alumno asociado para gestionar inscripciones.")
        return _redirect_target()


class CursilloInscripcionInstructorView(LoginRequiredMixin, TemplateView):
    """
    Inscripción masiva de alumnos por parte del instructor de su dojo o administradores.
    Soporta tanto Cinturones Negros como Cinturones de Color (cuando el cursillo lo admite).
    """
    template_name = 'administracion/inscripcion_instructor.html'
    cursillo = None

    def dispatch(self, request, *args, **kwargs):
        self.cursillo = get_object_or_404(Cursillo, pk=self.kwargs['pk'])
        user = request.user

        es_instructor = obtener_alumno_instructor(user) is not None
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
            alumnos_color_a_inscribir = form.cleaned_data.get('alumnos_color')

            instructor = obtener_alumno_instructor(request.user)
            if instructor and not (request.user.is_staff or request.user.is_superuser):
                dojo = instructor.dojo
                # Cinturones Negros del dojo del instructor
                alumnos_dojo_pks = set(Alumno.objects.filter(dojo=dojo, instructor=False, activo=True).values_list('pk', flat=True))
                selected_dojo_pks = set(alumnos_a_inscribir.values_list('pk', flat=True)) & alumnos_dojo_pks
                actuales_dojo_pks = set(self.cursillo.alumnos.filter(dojo=dojo).values_list('pk', flat=True))

                to_remove = actuales_dojo_pks - selected_dojo_pks
                to_add = selected_dojo_pks - actuales_dojo_pks

                if to_remove:
                    self.cursillo.alumnos.remove(*to_remove)
                if to_add:
                    self.cursillo.alumnos.add(*to_add)

                # Cinturones de Color del dojo del instructor (si el cursillo está abierto a grados Kyu)
                if self.cursillo.abierto_cintos_color and alumnos_color_a_inscribir is not None:
                    color_dojo_pks = set(AlumnoColor.objects.filter(dojo=dojo, activo=True).values_list('pk', flat=True))
                    selected_color_pks = set(alumnos_color_a_inscribir.values_list('pk', flat=True)) & color_dojo_pks
                    actuales_color_pks = set(self.cursillo.alumnos_color.filter(dojo=dojo).values_list('pk', flat=True))

                    color_remove = actuales_color_pks - selected_color_pks
                    color_add = selected_color_pks - actuales_color_pks
                    if color_remove:
                        self.cursillo.alumnos_color.remove(*color_remove)
                    if color_add:
                        self.cursillo.alumnos_color.add(*color_add)
            else:
                # Administrador global
                self.cursillo.alumnos.set(alumnos_a_inscribir)
                if self.cursillo.abierto_cintos_color and alumnos_color_a_inscribir is not None:
                    self.cursillo.alumnos_color.set(alumnos_color_a_inscribir)

            messages.success(request, "Se han actualizado las inscripciones correctamente.")
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
