"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views
from administracion.views import alumnos as alumnos_views
from administracion.views import alumnos_color as alumnos_color_views
from administracion.views import dojos as dojos_views
from administracion.views import dojo_portal as dojo_portal_views
from administracion.views import cursillos as cursos_views
from administracion.views import actividades as actividades_views
from administracion.views import tablon as tablon_views
from administracion.views import varios as varios_views
from administracion.views import directiva as directiva_views

# Asegúrate de tener un namespace
app_name = 'administracion'

urlpatterns = [
    # Alumnos (Cinturones Negros DAN)
    path("alumnos/", alumnos_views.AlumnosView.as_view(), name="alumnos"),
    path("alumnos/<int:pk>/", alumnos_views.AlumnoDetailView.as_view(), name="alumno_detalle"),
    path("alumnos/<int:pk>/invitar-usuario/", alumnos_views.AlumnoInvitarUsuarioView.as_view(), name="alumno_invitar_usuario"),
    path("alumnos/grado/<int:grado>/", alumnos_views.AlumnosView.as_view(), name="alumnos_grado"),
    # Alumnos de Cinturón de Color (Kyu y Menores - Aislamiento estricto RGPD)
    path("alumnos-color/", alumnos_color_views.AlumnosColorListView.as_view(), name="alumnos_color"),
    path("alumnos-color/nuevo/", alumnos_color_views.AlumnoColorCreateView.as_view(), name="alumno_color_nuevo"),
    path("alumnos-color/<uuid:codigo>/", alumnos_color_views.AlumnoColorDetailView.as_view(), name="alumno_color_detalle"),
    path("alumnos-color/<uuid:codigo>/editar/", alumnos_color_views.AlumnoColorUpdateView.as_view(), name="alumno_color_editar"),
    path("alumnos-color/<uuid:codigo>/ascenso/", alumnos_color_views.AlumnoColorAscensoView.as_view(), name="alumno_color_ascenso"),
    path("alumnos-color/<uuid:codigo>/invitar-usuario/", alumnos_color_views.AlumnoColorInvitarUsuarioView.as_view(), name="alumno_color_invitar_usuario"),
    path("alumnos-color/<uuid:codigo>/promocionar-dan/", alumnos_color_views.AlumnoColorPromocionDanView.as_view(), name="alumno_color_promocionar_dan"),
    path("alumnos-color/<uuid:codigo>/eliminar/", alumnos_color_views.AlumnoColorDeleteView.as_view(), name="alumno_color_eliminar"),
    # Dojos
    path("dojos/", dojos_views.DojosView.as_view(), name="dojos"),
    path("dojos/<int:pk>/", dojos_views.DojoDetailView.as_view(), name="dojo_detalle"),
    path("dojos/portal/<slug:slug>/", dojo_portal_views.DojoPortalView.as_view(), name="dojo_portal"),
    path("dojos/portal/<slug:slug>/configurar/", dojo_portal_views.DojoPortalConfigUpdateView.as_view(), name="dojo_portal_config"),
    # Cursillos
    path("cursillos/", cursos_views.CursillosView.as_view(), name="cursillos"),
    path("cursillos/<int:pk>/", cursos_views.CursilloDetailView.as_view(), name="cursillo_detalle"),
    path("cursillos/<int:pk>/examinados", cursos_views.CursilloExaminaListView.as_view(), name="cursillo_examinados"),
    path("cursillos/<int:pk>/estadisticas", cursos_views.CursilloEstadisticasView.as_view(), name="cursillo_estadisticas"),
    path("cursillos/<int:pk>/circular", cursos_views.descargar_circular, name="descargar_circular"),
    path("cursillos/<int:pk>/inscripcion", cursos_views.CursilloInscripcionInstructorView.as_view(), name="cursillo_inscripcion_instructor"),
    path("cursillos/<int:pk>/inscripcion-alumno", cursos_views.CursilloInscripcionAlumnoView.as_view(), name="cursillo_inscripcion_alumno"),
    path("curso/nuevo/", administracion_views.CursoNuevoView.as_view(), name="curso_nuevo"),
    # Peticiones
    path("peticiones/", administracion_views.PeticionView.as_view(), name="peticiones"),
    path("peticiones/anular/<int:pk>/", administracion_views.PeticionAnularView.as_view(), name="peticiones_anular"),
    # Directiva
    path("directiva/", directiva_views.DirectivaView.as_view(), name="directiva"),
    # Actividades
    path("actividades/", actividades_views.ActividadesView.as_view(), name="actividades"),
    path("actividades/editar/<int:pk>/", actividades_views.ActividadEditarView.as_view(), name="editar_actividad"),
    path("actividades/eliminar/<int:pk>/", actividades_views.ActividadEliminarView.as_view(), name="eliminar_actividad"),
    # Tablon
    path("tablon/", tablon_views.TablonView.as_view(), name="tablon"),
    path("tablon/editar/<int:pk>/", tablon_views.TablonEditarView.as_view(), name="editar_tablon"),
    path("tablon/eliminar/<int:pk>/", tablon_views.TablonEliminarView.as_view(), name="eliminar_tablon"),
    # Varios
    path("correo/", varios_views.enviar_correo_instructores, name="correo"),
    path("error/<int:error_code>/", varios_views.ErrorView.as_view(), name="errores"),
]
