"""Configuración URLs de usuarios"""

# Django
from django.urls import path
from django.contrib.auth import views as auth_views

# App usuarios
from usuarios import views as usuarios_views

# Formularios
from .forms import CustomPasswordResetForm

# Asegúrate de tener un namespace
#app_name = 'usuarios'

urlpatterns = [
    path("login/", usuarios_views.login_view, name="login"),
    path("logout/", usuarios_views.logout_view, name="logout"),
    path("cambio_password/", usuarios_views.cambio_password, name="cambio_password"),
    path("registro/", usuarios_views.registro_view, name="registro"),
    # Olvido contraseña. Paso 1: usuario introduce s email
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="usuarios/password_reset.html",
        form_class=CustomPasswordResetForm,
        from_email="ogkke@egalvez.es",
        html_email_template_name="usuarios/emails/email_reset_password.html",
        subject_template_name="usuarios/emails/email_reset_subject.txt",
        success_url="password_reset_hecho",
    ), name="password_reset"),
    # Olvido contraseña. Paso 2: confirmacion de que se envió el email
    path("password_reset/password_reset_hecho/", auth_views.PasswordResetDoneView.as_view(
        template_name="usuarios/password_reset_hecho.html",
    ), name="password_reset_hecho"),
    # Olvido contraseña. Paso 3: usuario introduce la contraseña
    path("password_reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="usuarios/password_reset_confirm.html",
    ), name="password_reset_confirm"),
    # Olvido contraseña. Paso 4: confirmación usuario ingresa la nueva contraseña
    path("password_reset/completo/", auth_views.PasswordResetCompleteView.as_view(
        template_name="usuarios/password_reset_completo.html",
    ), name="password_reset_completo"),
]
