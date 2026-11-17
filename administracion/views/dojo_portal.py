"""
Vistas del Portal Autónomo de Dojo y verificación On-Demand TLS para dominios propios.
Prepara la arquitectura Core Central OGKKE + Dojos locales con responsabilidades propias.
"""
import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, Subquery
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from administracion.forms import DojoPortalConfigForm, TablonNuevoForm
from administracion.middleware.dojo_tenant import (
    extract_clean_host,
    is_core_host,
    resolve_dojo_from_host,
)
from administracion.models import (
    Alumno,
    Cursillo,
    Dojo,
    Examen,
    Peticion,
    Tablon,
    obtener_tablon_intercalado,
)
from administracion.permissions import (
    es_alumno_solo_portal_dojo,
    obtener_dojo_usuario,
    obtener_perfiles_alumno,
)


def usuario_puede_gestionar_dojo(user, dojo):
    """
    Determina si el usuario autenticado tiene permisos de administración local
    sobre el Dojo indicado (Staff, Superusuario o Instructor titular de ese Dojo).
    """
    if not user or not user.is_authenticated or dojo is None:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return Alumno.objects.filter(usuario=user, dojo=dojo, instructor=True).exists()


class DojoPortalView(View):
    """
    Portal autónomo de un Dojo local:
    - Accesible por dominio propio (ej. https://karatesakura.es/),
      subdominio automático (https://sakura.ogkke.es/) o ruta (/dojo/<slug>/).
    - Aplica los Design Tokens de marca del Dojo (--dojo-accent).
    - Centraliza la información pública del centro, Sensei titular, horarios,
      Tablón de Anuncios local y conexión con eventos nacionales de OGKKE.
    """

    template_name = "administracion/dojo_portal.html"

    def get_dojo(self, request, slug=None):
        dojo = getattr(request, "current_dojo", None)
        if dojo is None and slug:
            dojo = get_object_or_404(Dojo, slug=slug)
        if dojo is None:
            raise Http404("Dojo no encontrado.")

        puede_gestionar = usuario_puede_gestionar_dojo(request.user, dojo)
        if not dojo.sitio_activo and not puede_gestionar:
            raise Http404("El portal de este Dojo no se encuentra activo actualmente.")

        request.current_dojo = dojo
        return dojo

    def get(self, request, slug=None):
        dojo = self.get_dojo(request, slug=slug)

        # Si el usuario autenticado es un alumno regular (DAN o Color), solo puede acceder al portal de su propio Dojo
        if request.user.is_authenticated and es_alumno_solo_portal_dojo(request.user):
            dojo_propio = obtener_dojo_usuario(request.user)
            if dojo_propio and dojo_propio.pk != dojo.pk and dojo_propio.slug:
                return redirect(reverse("administracion:dojo_portal", kwargs={"slug": dojo_propio.slug}))

        puede_gestionar = usuario_puede_gestionar_dojo(request.user, dojo)
        hoy = datetime.date.today()

        instructor = (
            Alumno.objects.select_related("usuario")
            .filter(dojo=dojo, instructor=True)
            .first()
        )
        tablon_particulares_qs = Tablon.objects.for_dojo(dojo).order_by("fecha", "id")
        tablon_qs = obtener_tablon_intercalado(tablon_particulares_qs)

        # Escalafón DAN del Dojo con la fecha del último examen realizado por cada compañero
        ultimo_examen_subquery = (
            Examen.objects.filter(alumno=OuterRef("pk"))
            .order_by("-evento__fecha", "-grado")
            .values("evento__fecha")[:1]
        )
        cintos_negros = list(
            Alumno.objects.filter(dojo=dojo, instructor=False, activo=True)
            .annotate(fecha_ultimo_examen=Subquery(ultimo_examen_subquery))
            .order_by("-grado", "apellidos", "nombre")
        )

        # Perfil personal del usuario logado si pertenece a este Dojo
        mi_alumno_dan = None
        mi_alumno_color = None
        mis_examenes_dan = []
        mis_examenes_kyu = []
        mis_cursillos_asistidos = []

        if request.user.is_authenticated:
            alumno_dan, alumno_color = obtener_perfiles_alumno(request.user)
            if alumno_dan and alumno_dan.dojo_id == dojo.id:
                mi_alumno_dan = alumno_dan
                examenes_qs = list(
                    Examen.objects.filter(alumno=alumno_dan)
                    .select_related("evento")
                    .order_by("evento__fecha")
                )
                for idx, exam in enumerate(examenes_qs):
                    if idx == len(examenes_qs) - 1:
                        anios_grado = max(0, hoy.year - exam.evento.fecha.year)
                    else:
                        siguiente_fecha = examenes_qs[idx + 1].evento.fecha
                        anios_grado = max(0, siguiente_fecha.year - exam.evento.fecha.year)
                    mis_examenes_dan.append((exam, anios_grado))
                mis_cursillos_asistidos = list(alumno_dan.cursillo_set.all().order_by("-fecha"))
            elif alumno_color and alumno_color.dojo_id == dojo.id:
                mi_alumno_color = alumno_color
                mis_examenes_kyu = list(
                    alumno_color.historial_grados.select_related("grado", "evaluador").order_by("-fecha_examen", "-grado__orden")
                )
                mis_cursillos_asistidos = list(alumno_color.cursillos_asistidos.all().order_by("-fecha"))

        proximos_cursillos = list(
            Cursillo.objects.filter(fecha__gte=hoy).order_by("fecha")[:5]
        )
        inscritos_dan_ids = (
            set(mi_alumno_dan.cursillo_set.filter(fecha__gte=hoy).values_list("id", flat=True))
            if mi_alumno_dan
            else set()
        )
        inscritos_color_ids = (
            set(mi_alumno_color.cursillos_asistidos.filter(fecha__gte=hoy).values_list("id", flat=True))
            if mi_alumno_color
            else set()
        )
        for curso in proximos_cursillos:
            if mi_alumno_dan:
                curso.usuario_inscrito = curso.id in inscritos_dan_ids
                curso.usuario_puede_inscribirse = not mi_alumno_dan.instructor
            elif mi_alumno_color:
                curso.usuario_inscrito = curso.id in inscritos_color_ids
                curso.usuario_puede_inscribirse = bool(curso.abierto_cintos_color)
            else:
                curso.usuario_inscrito = False
                curso.usuario_puede_inscribirse = False

        peticiones_pendientes = (
            Peticion.objects.for_dojo(dojo).filter(finalizada=False).count()
            if puede_gestionar
            else 0
        )

        lineas_horario = [
            linea.strip()
            for linea in (dojo.horario_resumen or "").splitlines()
            if linea.strip()
        ]

        context = {
            "dojo": dojo,
            "instructor": instructor,
            "tablon": tablon_qs,
            "tablon_particulares": tablon_particulares_qs,
            "cintos_negros_dojo": cintos_negros,
            "total_cintos_negros": len(cintos_negros),
            "proximos_cursillos": proximos_cursillos,
            "puede_gestionar_dojo": puede_gestionar,
            "peticiones_pendientes": peticiones_pendientes,
            "lineas_horario": lineas_horario,
            "mi_alumno_dan": mi_alumno_dan,
            "mi_alumno_color": mi_alumno_color,
            "mis_examenes_dan": mis_examenes_dan,
            "mis_examenes_kyu": mis_examenes_kyu,
            "mis_cursillos_asistidos": mis_cursillos_asistidos,
            "tablon_form": TablonNuevoForm(),
            "config_form": DojoPortalConfigForm(instance=dojo) if puede_gestionar else None,
            "dojo_base_domain": getattr(settings, "DOJO_BASE_DOMAIN", "ogkke.es"),
        }
        return render(request, self.template_name, context)


class DojoPortalConfigUpdateView(LoginRequiredMixin, View):
    """
    Permite al instructor titular del Dojo o al Staff actualizar la configuración
    del portal web del Dojo, su identidad visual (color/logo), horarios y dominio propio.
    """

    def post(self, request, slug):
        dojo = get_object_or_404(Dojo, slug=slug)
        if not usuario_puede_gestionar_dojo(request.user, dojo):
            raise PermissionDenied("No tienes permiso para configurar este Dojo.")

        form = DojoPortalConfigForm(request.POST, request.FILES, instance=dojo)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Configuración del portal y dominio de {dojo.nombre} actualizada correctamente.",
            )
        else:
            errores = "; ".join(
                f"{campo}: {', '.join(lista)}" for campo, lista in form.errors.items()
            )
            messages.error(request, f"No se pudo guardar la configuración del Dojo ({errores}).")

        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(reverse("administracion:dojo_portal", kwargs={"slug": dojo.slug}))


def tls_domain_check(request):
    """
    Endpoint interno para emisión automática de certificados SSL/TLS (Caddy On-Demand TLS).
    Ejemplo en Caddyfile:
        on_demand_tls {
            ask http://127.0.0.1:8000/internal/tls-check/
        }
    Devuelve 200 OK únicamente si el parámetro ?domain= pertenece al Core o a un Dojo con sitio_activo=True.
    """
    domain = request.GET.get("domain", "")
    clean = extract_clean_host(domain)
    if not clean:
        return HttpResponse("Missing domain parameter", status=400)

    if is_core_host(clean):
        return HttpResponse("OK (Core host)", status=200)

    dojo = resolve_dojo_from_host(clean)
    if dojo is not None:
        return HttpResponse(f"OK (Dojo: {dojo.slug})", status=200)

    return HttpResponse("Domain not authorized", status=403)
