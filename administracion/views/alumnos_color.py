"""
Vistas Basadas en Clases (CBV) para la gestión de Cinturones de Color (Kyu) y Menores.
Aplica aislamiento estricto por Dojo (Multi-Tenant), anti-IDOR mediante UUID y
protección de datos de menores (RGPD / LOPDGDD Art. 7).
"""
import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from administracion.forms import AlumnoColorForm, AscensoGradoKyuForm
from administracion.models import AlumnoColor, Dojo, GradoKyu, HistorialGradoKyu
from administracion.permissions import (
    InstructorOrStaffRequiredMixin,
    obtener_alumno_instructor,
    obtener_dojo_instructor,
    usuario_es_staff_asociacion,
)


def obtener_alumno_color_autorizado(user, codigo=None, pk=None):
    """
    Resuelve un AlumnoColor verificando estrictamente que pertenezca al ámbito
    permitido del usuario (Staff de la asociación o Instructor de ese mismo Dojo).
    Si el registro existe pero pertenece a otro Dojo, lanza PermissionDenied (403)
    para bloquear cualquier intento de acceso cruzado (IDOR).
    """
    lookup = {'codigo_interno': codigo} if codigo is not None else {'pk': pk}
    existe_global = AlumnoColor.objects.select_related('dojo', 'grado_actual').filter(**lookup).first()
    if existe_global is None:
        raise Http404("El alumno solicitado no existe.")

    autorizado = AlumnoColor.objects.for_user(user).filter(pk=existe_global.pk).exists()
    if not autorizado:
        raise PermissionDenied(
            "Protección de Datos (RGPD / LOPDGDD): No tiene autorización para acceder a datos de alumnos de otro Dojo."
        )
    return existe_global


class AlumnosColorListView(InstructorOrStaffRequiredMixin, ListView):
    """
    Listado y panel de gestión de Cinturones de Color (Kyu) y Menores.
    Solo accesible para el Instructor titular (ve exclusivamente su Dojo) y Staff de OGKKE.
    """
    model = AlumnoColor
    template_name = 'administracion/alumnos_color.html'
    context_object_name = 'alumnos_color'

    def get_queryset(self):
        qs = (
            AlumnoColor.objects.for_user(self.request.user)
            .select_related('dojo', 'grado_actual')
            .order_by('dojo__nombre', 'grado_actual__orden', 'apellidos', 'nombre')
        )
        dojo_filter = self.request.GET.get('dojo')
        if dojo_filter and dojo_filter.isdigit():
            qs = qs.filter(dojo_id=int(dojo_filter))

        grado_filter = self.request.GET.get('grado')
        if grado_filter and grado_filter.isdigit():
            qs = qs.filter(grado_actual_id=int(grado_filter))

        solo_activos = self.request.GET.get('activos')
        if solo_activos == '1':
            qs = qs.filter(activo=True)
        elif solo_activos == '0':
            qs = qs.filter(activo=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        es_staff = usuario_es_staff_asociacion(user)
        dojo_instructor = obtener_dojo_instructor(user)

        base_qs = AlumnoColor.objects.for_user(user).select_related('grado_actual', 'dojo')
        lista_actual = list(context['alumnos_color'])

        menores_14_count = sum(1 for a in lista_actual if a.es_menor_14)
        pendientes_rgpd_count = sum(1 for a in lista_actual if not a.tiene_autorizacion_valida)

        context.update({
            'es_staff_asociacion': es_staff,
            'dojo_instructor': dojo_instructor,
            'grados_kyu': GradoKyu.objects.all().order_by('orden'),
            'dojos_disponibles': Dojo.objects.all().order_by('nombre') if es_staff else Dojo.objects.filter(pk=dojo_instructor.pk) if dojo_instructor else Dojo.objects.none(),
            'total_alumnos_color': len(lista_actual),
            'total_global_permitido': base_qs.count(),
            'menores_14_count': menores_14_count,
            'pendientes_rgpd_count': pendientes_rgpd_count,
            'form_alta': AlumnoColorForm(user=user, initial={'fecha_ultimo_grado': datetime.date.today()}),
            'dojo_seleccionado': self.request.GET.get('dojo', ''),
            'grado_seleccionado': self.request.GET.get('grado', ''),
        })
        return context


class AlumnoColorCreateView(InstructorOrStaffRequiredMixin, View):
    """
    Crea un nuevo practicante de Cinturón de Color aplicando validaciones RGPD/LOPDGDD
    y forzando el Dojo del instructor cuando no es Staff.
    """

    def post(self, request):
        user = request.user
        es_staff = usuario_es_staff_asociacion(user)
        dojo_instructor = obtener_dojo_instructor(user)

        post_data = request.POST.copy()
        if not es_staff:
            if not dojo_instructor:
                raise PermissionDenied("No tiene ningún Dojo asignado como instructor.")
            dojo_enviado = post_data.get('dojo')
            if dojo_enviado and str(dojo_enviado) != str(dojo_instructor.pk):
                raise PermissionDenied("No puede dar de alta alumnos en un Dojo distinto al suyo.")
            post_data['dojo'] = str(dojo_instructor.pk)

        form = AlumnoColorForm(post_data, request.FILES, user=user)
        if form.is_valid():
            try:
                alumno_color = form.save()
                instructor_eval = obtener_alumno_instructor(user)
                HistorialGradoKyu.objects.create(
                    alumno_color=alumno_color,
                    grado=alumno_color.grado_actual,
                    fecha_examen=alumno_color.fecha_ultimo_grado or datetime.date.today(),
                    evaluador=instructor_eval,
                    observaciones="Grado inicial en el alta del alumno.",
                )
                messages.success(
                    request,
                    f"Alumno de color {alumno_color.nombre} {alumno_color.apellidos} registrado correctamente.",
                )
                return redirect('administracion:alumno_color_detalle', codigo=alumno_color.codigo_interno)
            except ValidationError as exc:
                messages.error(request, f"Error de validación RGPD/LOPDGDD: {'; '.join(exc.messages)}")
        else:
            errores = "; ".join(
                f"{campo}: {', '.join(err)}" for campo, err in form.errors.items()
            )
            messages.error(request, f"No se pudo registrar el alumno: {errores}")

        return redirect('administracion:alumnos_color')


class AlumnoColorDetailView(InstructorOrStaffRequiredMixin, DetailView):
    """
    Ficha detallada y protegida de un Alumno de Cinturón de Color, con historial
    de grados Kyu, estado de autorización paterna y participaciones en campeonatos.
    """
    model = AlumnoColor
    template_name = 'administracion/detalle_alumno_color.html'
    context_object_name = 'alumno_color'

    def get_object(self, queryset=None):
        codigo = self.kwargs.get('codigo')
        pk = self.kwargs.get('pk')
        return obtener_alumno_color_autorizado(self.request.user, codigo=codigo, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.object
        historial = alumno.historial_grados.select_related('grado', 'evaluador').all()
        inscripciones = alumno.inscripciones_campeonato.select_related(
            'categoria', 'categoria__campeonato', 'categoria__tatami'
        ).order_by('-categoria__campeonato__fecha_inicio')

        # Sugerir siguiente grado Kyu en orden jerárquico
        siguiente_grado = (
            GradoKyu.objects.filter(orden__gt=alumno.grado_actual.orden)
            .order_by('orden')
            .first()
        )
        form_ascenso = AscensoGradoKyuForm(initial={
            'nuevo_grado': siguiente_grado or alumno.grado_actual,
            'fecha_examen': datetime.date.today(),
        })
        form_edicion = AlumnoColorForm(instance=alumno, user=self.request.user)

        context.update({
            'historial_grados': historial,
            'inscripciones_torneos': inscripciones,
            'form_ascenso': form_ascenso,
            'form_edicion': form_edicion,
            'siguiente_grado': siguiente_grado,
        })
        return context


class AlumnoColorUpdateView(InstructorOrStaffRequiredMixin, View):
    """
    Actualización de datos y autorización RGPD/paterna de un Alumno de Cinturón de Color.
    """

    def post(self, request, codigo):
        alumno_color = obtener_alumno_color_autorizado(request.user, codigo=codigo)
        es_staff = usuario_es_staff_asociacion(request.user)
        post_data = request.POST.copy()

        if not es_staff:
            post_data['dojo'] = str(alumno_color.dojo_id)

        grado_anterior_id = alumno_color.grado_actual_id
        form = AlumnoColorForm(post_data, request.FILES, instance=alumno_color, user=request.user)
        if form.is_valid():
            actualizado = form.save()
            if actualizado.grado_actual_id != grado_anterior_id:
                HistorialGradoKyu.objects.create(
                    alumno_color=actualizado,
                    grado=actualizado.grado_actual,
                    fecha_examen=actualizado.fecha_ultimo_grado or datetime.date.today(),
                    evaluador=obtener_alumno_instructor(request.user),
                    observaciones="Actualización de grado desde ficha del alumno.",
                )
            messages.success(request, "Ficha del alumno actualizada correctamente.")
        else:
            errores = "; ".join(
                f"{campo}: {', '.join(err)}" for campo, err in form.errors.items()
            )
            messages.error(request, f"No se pudo actualizar la ficha: {errores}")

        return redirect('administracion:alumno_color_detalle', codigo=alumno_color.codigo_interno)


class AlumnoColorAscensoView(InstructorOrStaffRequiredMixin, View):
    """
    Registra un examen/pase de grado Kyu y actualiza el cinturón actual del alumno.
    """

    def post(self, request, codigo):
        alumno_color = obtener_alumno_color_autorizado(request.user, codigo=codigo)
        form = AscensoGradoKyuForm(request.POST)
        if form.is_valid():
            nuevo_grado = form.cleaned_data['nuevo_grado']
            fecha_examen = form.cleaned_data['fecha_examen']
            observaciones = form.cleaned_data.get('observaciones', '')

            alumno_color.grado_actual = nuevo_grado
            alumno_color.fecha_ultimo_grado = fecha_examen
            alumno_color.save()

            HistorialGradoKyu.objects.create(
                alumno_color=alumno_color,
                grado=nuevo_grado,
                fecha_examen=fecha_examen,
                evaluador=obtener_alumno_instructor(request.user),
                observaciones=observaciones or f"Ascenso a cinturón {nuevo_grado.nombre}",
            )
            messages.success(
                request,
                f"Ascenso registrado: {alumno_color.nombre} {alumno_color.apellidos} es ahora cinturón {nuevo_grado.nombre}.",
            )
        else:
            messages.error(request, "Datos de ascenso no válidos.")

        return redirect('administracion:alumno_color_detalle', codigo=alumno_color.codigo_interno)


class AlumnoColorDeleteView(InstructorOrStaffRequiredMixin, View):
    """
    Elimina (derecho de supresión RGPD) la ficha de un Alumno de Cinturón de Color
    verificando pertenencia al Dojo del instructor o rol Staff.
    """

    def post(self, request, codigo):
        alumno_color = obtener_alumno_color_autorizado(request.user, codigo=codigo)
        nombre_completo = f"{alumno_color.nombre} {alumno_color.apellidos}"
        alumno_color.delete()
        messages.success(request, f"Ficha de {nombre_completo} eliminada conforme a RGPD.")
        return redirect('administracion:alumnos_color')
