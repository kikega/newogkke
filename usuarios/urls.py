"""Configuración URLs de usuarios"""

# Django
from django.urls import path

# App usuarios
from usuarios import views as usuarios_views

urlpatterns = [
    path("login/", usuarios_views.login_view, name="login"),
    path("logout/", usuarios_views.logout_view, name="logout"),
    path("cambio_password/", usuarios_views.cambio_password, name="cambio_password"),
]
