"""Configuración URLs de administracion"""

# Django
from django.urls import path

# App usuarios
from administracion import views as administracion_views

urlpatterns = [
    path("home/", administracion_views.home, name="home"),
]
