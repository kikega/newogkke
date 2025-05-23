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
    #path("alumnos/grado/<int:grado>/<int:pk>/", administracion_views.AlumnoDetailView.as_view(), name="alumno_detalle"),
    path("alumnos/grado/<int:grado>/", administracion_views.AlumnosView.as_view(), name="alumnos_grado"),
    path("dojos/", administracion_views.DojosView.as_view(), name="dojos"),
    path("dojos/<int:pk>/", administracion_views.DojoDetailView.as_view(), name="dojo_detalle"),
    path("cursillos/", administracion_views.CursillosView.as_view(), name="cursillos"),
    path("cursillos/<int:pk>/", administracion_views.CursilloDetailView.as_view(), name="cursillo_detalle"),
    path("cursillos/<int:pk>/examinados", administracion_views.CursilloExaminaListView.as_view(), name="cursillo_examinados"),
    path("peticiones/", administracion_views.PeticionView.as_view(), name="peticiones"),
    path("peticiones/anular/<int:pk>/", administracion_views.PeticionAnularView.as_view(), name="peticiones_anular"),
    path("correo/", administracion_views.CorreoView.as_view(), name="correo"),
]
