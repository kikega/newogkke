"""
Vistas relacionadas con la gestión de peticiones
"""

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View, TemplateView
from django.conf import settings

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
            try:
                # Obtiene una instancia de alumno para el usuario actual
                alumno = Alumno.objects.select_related('dojo').get(usuario=user)
                dojo_usuario = alumno.dojo
                # Obtenemos todas las peticiones pendientes si el usuario es staff o superuser
                # En caso sontrario las del dojo actual
                if user.is_staff or user.is_superuser:
                    peticiones_pendientes = Peticion.objects.filter(
                        finalizada=False
                    ).order_by('-fecha')
                else:
                    peticiones_pendientes = Peticion.objects.filter(
                        dojo=dojo_usuario,
                        finalizada=False
                    ).order_by('-fecha')
            except Alumno.DoesNotExist: # pylint: disable=no-member
                redirect ('administracion:error', context={'error_code': 404, 'error_message': 'No se encontró el usuario'})

        # Almacena el objeto dojo y sus peticiones pendientes
        context ['dojo_usuario'] = dojo_usuario
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

        # Validar que los campos no estén vacíos
        # if not all([titulo, tipo, dojo_id, descripcion]):
        #     return render(request, self.template_name, {
        #         'error': 'Por favor, complete todos los campos.',
        #         'dojos': Dojo.objects.all()
        #     })

        # Obtenemos las plantillas HTML y TXT para el correo
        template_name_html='administracion/emails/notificacion_peticion.html',
        template_name_texto='administracion/emails/notificacion_peticion.txt',

        # Obtener el Dojo
        dojo = get_object_or_404(Dojo, pk=dojo_id)

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
    Anula una petición
    """

    def post(self, request, pk):
        peticion = get_object_or_404(Peticion, pk=pk)
        peticion.finalizada = True
        peticion.save()

        return redirect('administracion:peticiones')
