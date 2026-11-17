"""
Módulo centralizado de Control de Acceso Basado en Roles (RBAC),
aislamiento Multi-Tenant por Dojo (RGPD / LOPDGDD) y confinamiento
temporal de Jueces Efímeros de Tatami.
"""
import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from administracion.models import Alumno


JUEZ_TATAMI_GROUP_NAME = "JuezTatami"


def obtener_alumno_instructor(user):
    """
    Devuelve la instancia de Alumno si el usuario autenticado es un instructor activo.
    """
    if not user or not user.is_authenticated:
        return None
    return (
        Alumno.objects.select_related('dojo')
        .filter(usuario=user, instructor=True, activo=True)
        .first()
    )


def obtener_dojo_instructor(user):
    """
    Devuelve el Dojo que administra el instructor autenticado, o None si no es instructor.
    """
    inst = obtener_alumno_instructor(user)
    return inst.dojo if inst else None


def usuario_es_staff_asociacion(user):
    """Indica si el usuario pertenece al Staff o Superusuarios de la asociación nacional."""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def usuario_es_instructor_o_staff(user):
    """Indica si el usuario es Staff de la asociación o Instructor titular activo de un Dojo."""
    if usuario_es_staff_asociacion(user):
        return True
    return obtener_alumno_instructor(user) is not None


def es_usuario_juez_efimero(user):
    """
    Determina si un usuario es una cuenta efímera de Juez / Mesa de Tatami
    (pertenece al grupo JuezTatami o tiene tatamis asignados sin ser Staff ni Alumno de la asociación).
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return False
    if Alumno.objects.filter(usuario=user).exists():
        return False
    if user.groups.filter(name=JUEZ_TATAMI_GROUP_NAME).exists():
        return True
    from campeonatos.models import Tatami
    return Tatami.objects.filter(juez_operador=user).exists()


def obtener_tatamis_activos_juez(user, fecha_ref=None):
    """
    Devuelve el QuerySet de Tatamis asignados al usuario cuyo campeonato se encuentra
    dentro de sus fechas activas [fecha_inicio, fecha_fin] y no está finalizado.
    """
    from campeonatos.models import Tatami
    if not user or not user.is_authenticated:
        return Tatami.objects.none()
    ref = fecha_ref or datetime.date.today()
    return (
        Tatami.objects.select_related('campeonato')
        .filter(
            juez_operador=user,
            campeonato__fecha_inicio__lte=ref,
            campeonato__fecha_fin__gte=ref,
        )
        .exclude(campeonato__estado='FINALIZADO')
    )


def verificar_vigencia_login_juez(user, fecha_ref=None):
    """
    Verifica si un usuario puede iniciar o mantener sesión en el sistema.
    Si es un Juez de Tatami efímero y la fecha actual está fuera del rango
    [fecha_inicio, fecha_fin] del torneo (o el torneo ya finalizó), deniega el acceso.
    """
    if not es_usuario_juez_efimero(user):
        return True, None

    tatamis_vigentes = obtener_tatamis_activos_juez(user, fecha_ref=fecha_ref)
    if tatamis_vigentes.exists():
        return True, None

    return (
        False,
        "El acceso de Juez de Tatami solo está habilitado durante las fechas oficiales del campeonato.",
    )


class InstructorOrStaffRequiredMixin(LoginRequiredMixin):
    """
    Mixin para Vistas Basadas en Clases (CBV) que restringe el acceso exclusivamente
    a Instructores titulares de un Dojo o al Staff de la Asociación.
    Bloquea alumnos regulares y jueces efímeros con 403 PermissionDenied.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not usuario_es_instructor_o_staff(request.user):
            raise PermissionDenied(
                "Acceso restringido: solo los instructores de Dojo y el Staff de OGKKE pueden acceder a esta sección."
            )
        return super().dispatch(request, *args, **kwargs)
