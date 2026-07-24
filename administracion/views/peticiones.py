"""
Vistas relacionadas con la gestión de peticiones
"""

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View, TemplateView
from django.conf import settings
from django.core.exceptions import PermissionDenied

# App administracion
from administracion.models import Alumno, Dojo, Peticion

# Utilidades
from administracion.utils import enviar_correo_html

class PeticionView(LoginRequiredMixin, TemplateView):
    """
    Vista para realizar peticiones
    Procesa el formulario de petición y crea la petición en la BBDD.
    Obtiene los datos de la petición para mostrarlos en el template
    Si el usuario es staff, obtiene todas las peticiones pendiente
    Si el usuario es instructor, obtiene las peticiones pendientes del dojo actual
    """
    template_name = 'administracion/peticiones.html'
    context_object_name = 'peticion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtenemos los datos del usuario logado
        user = self.request.user

        # Inicializamos las variables
        # Esto garantiza que estas variables de contexto siempre existan,
        # incluso si el usuario no está asociado a un Dojo.
        dojo_usuario = None
        peticiones_pendientes = Peticion.objects.none()

        # Obtenemos los datos del dojo y sus peticiones pendientes
        if user.is_authenticated:
            if user.is_staff or user.is_superuser:
                peticiones_pendientes = Peticion.objects.filter(
                    finalizada=False
                ).order_by('-fecha')
                try:
                    alumno = Alumno.objects.select_related('dojo').get(usuario=user)
                    dojo_usuario = alumno.dojo
                except Alumno.DoesNotExist:
                    pass
            else:
                try:
                    # Obtiene una instancia de alumno para el usuario actual
                    alumno = Alumno.objects.select_related('dojo').get(usuario=user)
                    dojo_usuario = alumno.dojo
                    peticiones_pendientes = Peticion.objects.filter(
                        dojo=dojo_usuario,
                        finalizada=False
                    ).order_by('-fecha')
                except Alumno.DoesNotExist:
                    pass

        # Almacena el objeto dojo y sus peticiones pendientes
        context['dojo_usuario'] = dojo_usuario
        context['peticiones_pendientes'] = peticiones_pendientes
        context['user'] = user

        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de petición y crea la petición en la BBDD.
        """
        # Obtenemos las variables del formulario
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo')
        dojo_id = request.POST.get('dojo')
        descripcion = request.POST.get('descripcion')
        destinatario = settings.EMAIL_DEFAULT_STAFF

        # Obtener el Dojo
        dojo = get_object_or_404(Dojo, pk=dojo_id)

        # Verificar autorización:
        # Solo administradores o el instructor correspondiente del dojo pueden crear peticiones
        if not (request.user.is_staff or request.user.is_superuser):
            try:
                alumno = Alumno.objects.get(usuario=request.user)
                if not (alumno.instructor and alumno.dojo == dojo):
                    raise PermissionDenied("No tienes permiso para crear peticiones en este dojo.")
            except Alumno.DoesNotExist:
                raise PermissionDenied("No tienes permiso para crear peticiones.")

        # Obtenemos las plantillas HTML y TXT para el correo
        template_name_html='administracion/emails/notificacion_peticion.html',
        template_name_texto='administracion/emails/notificacion_peticion.txt',

        # Crear la petición
        Peticion.objects.create(
            titulo=titulo,
            tipo=tipo,
            dojo=dojo,
            descripcion=descripcion
        )

        # Convertimos el objeto creado un un diccionario
        peticion = {
            'titulo': titulo,
            'dojo': dojo.nombre,
            'email': request.user.email,
            'descripcion': descripcion,
        }
        contexto = {
            'peticion': peticion,
        }

        # Enviamos el correo electrónico
        enviar_correo_html(
            asunto = f'Nueva petición de {dojo.nombre}: {titulo}',
            template_name_html=template_name_html,
            template_name_texto=template_name_texto,
            contexto = contexto,
            destinatarios = destinatario,
        )

        return redirect('administracion:peticiones')


class PeticionAnularView(LoginRequiredMixin, View):
    """
    Anula o elimina una petición
    """

    def post(self, request, pk):
        peticion = get_object_or_404(Peticion, pk=pk)

        # Verificar autorización:
        # Administradores pueden anular/borrar cualquier petición.
        # Instructores del dojo asociado pueden anular/borrar.
        if not (request.user.is_staff or request.user.is_superuser):
            try:
                alumno = Alumno.objects.get(usuario=request.user)
                if not (alumno.instructor and alumno.dojo == peticion.dojo):
                    raise PermissionDenied("No tienes permiso para gestionar esta petición.")
            except Alumno.DoesNotExist:
                raise PermissionDenied("No tienes permiso para gestionar esta petición.")

        action = request.POST.get('action')
        if action == 'borrar':
            peticion.delete()
        else:
            peticion.finalizada = True
            peticion.save()

        return redirect('administracion:peticiones')
