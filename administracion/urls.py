"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views

# Asegúrate de tener un namespace
app_name = 'administracion'

urlpatterns = [
    path("alumnos/", administracion_views.AlumnosView.as_view(), name="alumnos"),
    path("alumnos/<int:pk>/", administracion_views.AlumnoDetailView.as_view(), name="alumno_detalle"),
    path("alumnos/grado/<int:grado>/", administracion_views.AlumnosView.as_view(), name="alumnos_grado"),
    path("dojos/", administracion_views.DojosView.as_view(), name="dojos"),
    path("dojos/<int:pk>/", administracion_views.DojoDetailView.as_view(), name="dojo_detalle"),
    path("cursillos/", administracion_views.CursillosView.as_view(), name="cursillos"),
    path("cursillos/<int:pk>/", administracion_views.CursilloDetailView.as_view(), name="cursillo_detalle"),
    path("cursillos/<int:pk>/examinados", administracion_views.CursilloExaminaListView.as_view(), name="cursillo_examinados"),
    path("cursillos/<int:pk>/estadisticas", administracion_views.CursilloEstadisticasView.as_view(), name="cursillo_estadisticas"),
    path("cursillos/<int:pk>/circular", administracion_views.descargar_circular, name="descargar_circular"),
    path("cursillos/<int:pk>/inscripcion", administracion_views.CursilloInscripcionInstructorView.as_view(), name="cursillo_inscripcion_instructor"),
    path("curso/nuevo/", administracion_views.CursoNuevoView.as_view(), name="curso_nuevo"),
    path("peticiones/", administracion_views.PeticionView.as_view(), name="peticiones"),
    path("tablon/", administracion_views.TablonView.as_view(), name="tablon"),
    path("peticiones/anular/<int:pk>/", administracion_views.PeticionAnularView.as_view(), name="peticiones_anular"),
    path("correo/", administracion_views.enviar_correo_instructores, name="correo"),
    path("error/<int:error_code>/", administracion_views.ErrorView.as_view(), name="errores"),
    path("actividades/", administracion_views.ActividadesView.as_view(), name="actividades"),
    path("actividades/<int:pk>/", administracion_views.ActividadEditarView.as_view, name="editar_actividad")
]
