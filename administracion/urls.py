"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views

urlpatterns = [
    path("alumnos/", administracion_views.Alumnos_View.as_view(), name="alumnos"),
    path("dojos/", administracion_views.Dojos_View.as_view(), name="dojos"),
]
