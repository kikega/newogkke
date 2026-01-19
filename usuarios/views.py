"""Views de la app usuarios"""
import logging

from django.shortcuts import render, redirect
from django.conf import settings

# Autenticacion
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.views.generic import FormView

# Django
from django.contrib import messages
from django.views.generic import TemplateView
from django.urls import reverse_lazy

# Modelos
from administracion.models import Alumno, Dojo
from .models import Usuario

# Formularios
from .forms import CreaUsuarioForm, UsuarioSelectDojoForm

# Utilidades
from administracion.utils import enviar_correo_html, validar_cadena

logger = logging.getLogger('access_logger')

def get_client_ip(request):
    """Obtiene la IP del cliente desde el encabezado X-Forwarded-For o Remote-Addr"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def login_view(request):
    """Vista para hacer login en la aplicación"""
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)

        if user:
            login(request, user)
            # Registro en el log con datos del usuario
            logger.info(f"Login exitoso - Usuario: {user.username} - {user.email}, IP: {get_client_ip(request)}")
            return redirect('home')
        else:
            return render(request, 'usuarios/login.html', {'error': 'Usuario o password incorrecto'})

    return render(request, 'usuarios/login.html')

def registro_view(request):
    """Vista para hacer registro de un alumno en la aplicación"""

    if request.method == 'POST':
        form = UsuarioSelectDojoForm(request.POST)
        if form.is_valid():
            dojo = form.cleaned_data['dojo']
    else:
        form = UsuarioSelectDojoForm()

    return render(request, 'usuarios/registro.html', {'form': form})


@login_required
def logout_view(request):
    """Vista para hacer logout en la aplicación"""
    logout(request)
    return redirect('login')


@login_required
def cambio_password(request):
    """Vista para cambiar contraseña"""
    # Obtenemos la foto del usuario logado
    try:
        usuario_foto = Alumno.objects.select_related('usuario').get(usuario__email=request.user.email)
    except Alumno.DoesNotExist: # pylint: disable=no-member
        usuario_foto = None

    if request.method == 'POST':
        old_password = request.POST['old_password']
        # Check de la contraseña introducida con la del usuario logado
        if check_password(old_password, request.user.password):
            new_password = request.POST['new_password']
            new_password_conf = request.POST['new_password_conf']
            if new_password != new_password_conf:
                return render(request, 'usuarios/cambio_password.html', {
                    'error': 'Las contraseñas no coinciden',
                    'usuario_foto': usuario_foto.foto,
                })
            user = Usuario.objects.get(email=request.user.email)
            user.set_password(new_password)
            user.save()
            logger.info(f"Cambio de contraseña exitoso - Usuario: {request.user.username} - {request.user.email}, IP: {get_client_ip(request)}")
            # Una vez salvada la nueva contraseña hacemos logout del usuario
            logout(request)
            return redirect('login')
        else:
            return render(request, 'usuarios/cambio_password.html', {
                'error': 'Contraseña incorrecta',
                'usuario_foto': usuario_foto.foto,
            })

# class ResetPasswordView(FormView):
#     """
#     Vista para procesar la recuperacion de la contraseña
#     """

#     User = get_user_model()
#     template_name = "usuarios/reset_password.html"
#     form_class = ResetPasswordForm
#     success_url = reverse_lazy("login")

#     # Obtenemos las plantillas HTML y TXT para el correo
#     template_name_html='administracion/emails/notificacion_peticion.html',
#     template_name_texto='administracion/emails/notificacion_peticion.txt',

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Obtenemos todos los dojos
#         dojos = Dojo.objects.all().order_by('nombre')
#         context['dojos'] = dojos
#         return context
    
#     def form_valid(self, form):
#         """
#         Si el formulario es válido, enviamos el correo con las instrucciones para restablecer la contraseña
#         """
#         email = form.cleaned_data['email']

#         try:
#             user = self.User.objects.get(email=email)
#             alumno = Alumno.objects.select_related("usuario").get(usuario__email=email)
            
#             messages.success(self.request, "Se ha enviado un correo electrónico con las instrucciones para restablecer la contraseña.")
#         except Exception as e:
#             logger.exception("Error al enviar el correo de recuperacion: %s", e)
#             form.add_error(None, "Ocurrió un error al enviar el correo electrónico")
#         return super().form_valid(form)
    