"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views

urlpatterns = [
    path("alumnos/", administracion_views.AlumnosView.as_view(), name="alumnos"),
    #path("alumnos/<int:grado>/", administracion_views.AlumnosView.as_view(), name="alumnos"),
    path("dojos/", administracion_views.DojosView.as_view(), name="dojos"),
    path("cursillos/", administracion_views.Cursillos_View, name="cursillos"),
]
