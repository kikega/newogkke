"""
Vistas relacionadas con la gestión de los alumnos (Cinturones Negros DAN)
"""

# Python
import datetime
import json

# Django
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView

# App administracion
from administracion.forms import InvitarUsuarioAlumnoForm
from administracion.models import Alumno, Examen
from administracion.permissions import (
    InstructorOrStaffRequiredMixin,
    obtener_dojo_instructor,
    obtener_dojo_usuario,
    usuario_es_instructor_o_staff,
    usuario_es_staff_asociacion,
)
from administracion.utils import invitar_o_vincular_usuario_alumno


class AlumnosView(InstructorOrStaffRequiredMixin, ListView):
    """
    Vista global de alumnos por grado DAN (Solo Usuarios Globales: Staff, Instructores y Directiva)
    """
    model = Alumno
    template_name = 'administracion/alumnos.html'
    context_object_name = 'alumnos'
    # paginate_by = 10


    def get_template_names(self):
        if (
            self.request.headers.get("HX-Request") == "true"
            and self.request.headers.get("HX-Boosted") != "true"
        ):
            return ["administracion/partials/alumnos_grado_panel.html"]
        return [self.template_name]

    def get_queryset(self):
        """
        Define la consulta para obtener los alumnos por grado.
        Filtra por el grado obtenido en los parametros de la url
        Ordena los resultados
        """
        grado = self.kwargs.get('grado', 1)
        return (
            super()
            .get_queryset()
            .select_related('dojo')
            .filter(grado=grado)
            .order_by('dojo', 'apellidos')
        )


    def get_context_data(self, **kwargs):
        """
        Obtenemos los datos de los cintos negros para hacer el gráfico de barras completo
        """
        context = super().get_context_data(**kwargs)
        grado = self.kwargs.get('grado', 1)
        context['grado'] = grado

        # Obtenemos los datos completos del 1º al 10º DAN
        data = Alumno.objects.exclude(grado__isnull=True).values('grado').annotate(total=Count('id'))
        counts_by_grado = {item['grado']: item['total'] for item in data}
        labels = [f"{g}º DAN" for g in range(1, 11)]
        values = [counts_by_grado.get(g, 0) for g in range(1, 11)]

        data_json = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': 'Número de alumnos por grado',
        })
        context['data_json'] = data_json

        if self.context_object_name in context:
            context['cantidad'] = context[self.context_object_name].count()
        else:
            context['cantidad'] = self.get_queryset().count()

        context['grados_posibles'] = list(range(1, 11))
        return context


class AlumnoDetailView(InstructorOrStaffRequiredMixin, DetailView):
    """
    Muestra los detalles de un alumno específico en el Core Nacional:
    Exámenes ordenados cronológicamente, tiempo de permanencia en cada grado y cursillos asistidos.
    - Exclusivo para Usuarios Globales (Staff, Superusuarios, Instructores y Directiva).
    - Los alumnos regulares consultan su propio historial directamente dentro del Portal de su Dojo.
    """
    model = Alumno
    template_name = 'administracion/detalle_alumno.html'
    context_object_name = 'alumno'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.get_object()
        hoy = datetime.date.today()

        # Obtenemos la lista de exámenes de ese alumno ordenados por fecha
        examenes = list(Examen.objects.filter(alumno=alumno).select_related('evento').order_by('evento__fecha'))

        anios = []
        examen = []
        for idx, exam in enumerate(examenes):
            examen.append(f"{exam.grado}º DAN")
            if idx == len(examenes) - 1:
                anios_grado = max(0, hoy.year - exam.evento.fecha.year)
            else:
                siguiente_fecha = examenes[idx + 1].evento.fecha
                anios_grado = max(0, siguiente_fecha.year - exam.evento.fecha.year)
            anios.append(anios_grado)

        context['examen'] = examen
        context['examenes'] = examenes
        context['hoy'] = hoy
        context['anios'] = anios
        context['total_anios'] = sum(anios)
        context['examenes_anios'] = list(zip(examenes, anios))
        context['cursillos_asistidos'] = alumno.cursillo_set.all().order_by('-fecha')

        # Cálculo exacto de la edad
        edad = alumno.edad
        context['edad'] = edad

        user = self.request.user
        puede_gestionar_acceso = bool(
            usuario_es_staff_asociacion(user)
            or (obtener_dojo_instructor(user) == alumno.dojo)
        )
        context['puede_gestionar_acceso'] = puede_gestionar_acceso
        context['form_invitar_usuario'] = InvitarUsuarioAlumnoForm(
            initial={'email': alumno.usuario.email if alumno.usuario else ''}
        )

        # Datos del gráfico de años en cada grado
        data_json = json.dumps({
            'labels': examen,
            'values': anios,
            'titulo': 'Años en cada grado',
        })
        context['data_json'] = data_json

        return context


class AlumnoInvitarUsuarioView(InstructorOrStaffRequiredMixin, View):
    """
    Permite al Instructor titular del Dojo o al Staff activar/invitar a un Alumno (Cinto Negro)
    mayor de edad enviándole por email el enlace para establecer su contraseña.
    """

    def post(self, request, pk):
        alumno = get_object_or_404(Alumno.objects.select_related('dojo', 'usuario'), pk=pk)
        es_staff = usuario_es_staff_asociacion(request.user)
        dojo_instructor = obtener_dojo_instructor(request.user)

        if not es_staff and dojo_instructor != alumno.dojo:
            raise PermissionDenied("No tienes permiso para gestionar el acceso de alumnos de otro Dojo.")

        if alumno.es_menor_edad:
            messages.error(
                request,
                "Los menores de 18 años no pueden tener cuenta de acceso en la aplicación; sus gestiones las realiza el instructor del Dojo.",
            )
            return redirect('administracion:alumno_detalle', pk=alumno.pk)

        form = InvitarUsuarioAlumnoForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                invitar_o_vincular_usuario_alumno(alumno, email, request)
                messages.success(
                    request,
                    f"Se ha activado la cuenta y enviado el correo de invitación a {email} para acceder al portal de {alumno.dojo.nombre}.",
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            except Exception as exc:
                messages.error(request, f"Se vinculó la cuenta pero ocurrió un error al enviar el correo: {exc}")
        else:
            messages.error(request, "Introduce una dirección de correo electrónico válida.")

        return redirect('administracion:alumno_detalle', pk=alumno.pk)



