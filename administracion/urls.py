"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views
from administracion.views import alumnos as alumnos_views
from administracion.views import dojos as dojos_views
from administracion.views import cursillos as cursos_views
from administracion.views import actividades as actividades_views
from administracion.views import tablon as tablon_views
from administracion.views import varios as varios_views

# Asegúrate de tener un namespace
app_name = 'administracion'

urlpatterns = [
    # Alumnos
    path("alumnos/", alumnos_views.AlumnosView.as_view(), name="alumnos"),
    path("alumnos/<int:pk>/", alumnos_views.AlumnoDetailView.as_view(), name="alumno_detalle"),
    path("alumnos/grado/<int:grado>/", alumnos_views.AlumnosView.as_view(), name="alumnos_grado"),
    # Dojos
    path("dojos/", dojos_views.DojosView.as_view(), name="dojos"),
    path("dojos/<int:pk>/", dojos_views.DojoDetailView.as_view(), name="dojo_detalle"),
    # Cursillos
    path("cursillos/", cursos_views.CursillosView.as_view(), name="cursillos"),
    path("cursillos/<int:pk>/", cursos_views.CursilloDetailView.as_view(), name="cursillo_detalle"),
    path("cursillos/<int:pk>/examinados", cursos_views.CursilloExaminaListView.as_view(), name="cursillo_examinados"),
    path("cursillos/<int:pk>/estadisticas", cursos_views.CursilloEstadisticasView.as_view(), name="cursillo_estadisticas"),
    path("cursillos/<int:pk>/circular", cursos_views.descargar_circular, name="descargar_circular"),
    path("cursillos/<int:pk>/inscripcion", cursos_views.CursilloInscripcionInstructorView.as_view(), name="cursillo_inscripcion_instructor"),
    path("curso/nuevo/", administracion_views.CursoNuevoView.as_view(), name="curso_nuevo"),
    # Peticiones
    path("peticiones/", administracion_views.PeticionView.as_view(), name="peticiones"),
    path("peticiones/anular/<int:pk>/", administracion_views.PeticionAnularView.as_view(), name="peticiones_anular"),
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
