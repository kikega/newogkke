""" Vistas de la app administracion """

# Python
import datetime
import json

# Django

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from django.db.models import Count, Q

# App administracion
from administracion.models import Alumno, Cursillo, Dojo, Actividad
from administracion.permissions import (
    es_usuario_juez_efimero,
    obtener_dojo_usuario,
    obtener_tatamis_activos_juez,
    usuario_es_instructor_o_staff,
)

def home(request):
    """
    Punto de entrada raíz (/):
    - Si la petición llega por el subdominio o dominio propio de un Dojo activo,
      sirve directamente su Portal de Dojo autónomo.
    - Si llega por el dominio del Core Nacional, requiere autenticación y muestra
      el panel nacional de OGKKE a usuarios globales, o redirige al alumno al portal de su Dojo.
    """
    if getattr(request, "is_dojo_host", False) and getattr(request, "current_dojo", None):
        from administracion.views.dojo_portal import DojoPortalView
        return DojoPortalView.as_view()(request, slug=request.current_dojo.slug)
    return _core_home(request)


@login_required
def _core_home(request):
    """
    Home del Core Nacional de la aplicación.
    Si el usuario autenticado es un alumno (Cinto Negro o Color), lo redirige
    automáticamente al portal de su Dojo.
    """
    user = request.user
    if es_usuario_juez_efimero(user):
        tatami_activo = obtener_tatamis_activos_juez(user).first()
        if tatami_activo:
            return redirect(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami_activo.id}))
        raise PermissionDenied("Acceso restringido a su Tatami activo.")

    if not usuario_es_instructor_o_staff(user):
        dojo_usuario = obtener_dojo_usuario(user)
        if dojo_usuario and dojo_usuario.slug:
            return redirect(reverse('administracion:dojo_portal', kwargs={'slug': dojo_usuario.slug}))
        raise PermissionDenied("Acceso restringido al personal técnico e instructores de OGKKE.")

    hoy = datetime.date.today()
    actividades = Actividad.objects.filter(fecha__gte=hoy).order_by('fecha')
    cn = Alumno.objects.count()
    dojos = Dojo.objects.count()

    # Consulta única agregada para métricas de cursillos
    cursillos_stats = Cursillo.objects.aggregate(
        total=Count('id'),
        nacional=Count('id', filter=Q(pais__iexact='España')),
        internacional=Count('id', filter=Q(internacional=True)),
        extranjero=Count('id', filter=~Q(pais__iexact='España'))
    )

    # Mapeo completo y sincronizado de 1º a 10º DAN
    data = Alumno.objects.exclude(grado__isnull=True).values('grado').annotate(total=Count('id'))
    counts_by_grado = {item['grado']: item['total'] for item in data}
    labels = [f"{g}º DAN" for g in range(1, 11)]
    values = [counts_by_grado.get(g, 0) for g in range(1, 11)]

    data_json = json.dumps({
        'labels': labels,
        'values': values,
        'titulo': 'Número de alumnos por grado',
    })

    return render(request, 'administracion/home.html', {
        'cn': cn,
        'cursos': cursillos_stats['total'] or 0,
        'nacional': cursillos_stats['nacional'] or 0,
        'internacional': cursillos_stats['internacional'] or 0,
        'extranjero': cursillos_stats['extranjero'] or 0,
        'dojos': dojos,
        'hoy': hoy,
        'actividades': actividades,
        'data_json': data_json,
    })