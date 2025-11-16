"""
Vistas para varias acciones
"""

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib import messages


# Formularios
from administracion.forms import EmailInstructoresForm 

# Utilidades
from administracion.utils import enviar_correo_html, validar_cadena

class ErrorView(LoginRequiredMixin, TemplateView):
    """
    Página donde se definen los errores que se procuden
    """
    template_name = 'administracion/error.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtenemos el codigo de error
        error_code = self.kwargs.get('error_code')

        if error_code == 403:
            error_message = "Se han introducido caracteres no validos en algún campo del formulario. Sólo se permiten caracteres alfanuméricos y espacios."

        context['error_message'] = error_message
        context['error_code'] = error_code

        return context


@login_required
def enviar_correo_instructores(request):
    """
    Envío de correo a instructores
    """

    # Obtenemos las plantillas HTML y TXT para el correo
    template_name_html='administracion/emails/notificacion_peticion.html',
    template_name_texto='administracion/emails/notificacion_peticion.txt',

    if request.method == 'POST':
        form = EmailInstructoresForm(request.POST)
        if form.is_valid():
            instructores_seleccionados = form.cleaned_data['instructores']
            asunto = form.cleaned_data['asunto']
            mensaje_base = form.cleaned_data['mensaje']

            emails_destinatarios = []
            datatuple = [] # Para send_mass_mail

            for alumno_instructor in instructores_seleccionados:
                if alumno_instructor.usuario and alumno_instructor.usuario.email:
                    emails_destinatarios.append(alumno_instructor.usuario.email)
                    # Personalizar el mensaje para cada instructor si es necesario
                    mensaje_personalizado = f"Hola {alumno_instructor.nombre},\n\n{mensaje_base}"
                    datatuple.append((asunto, mensaje_personalizado, settings.DEFAULT_FROM_EMAIL, [alumno_instructor.usuario.email]))
                else:
                    messages.warning(request, f"El instructor {alumno_instructor.nombre} {alumno_instructor.apellidos} no tiene un email asociado y no se le enviará correo.")

            if datatuple:
                try:
                    enviar_correo_html(
                        asunto = asunto,
                        template_name_html=template_name_html,
                        template_name_texto=template_name_texto,
                        contexto = mensaje_base,
                        destinatarios = emails_destinatarios,
                    )
                    #send_mass_mail(datatuple, fail_silently=False)
                    messages.success(request, f"Correo enviado exitosamente a {len(datatuple)} instructor(es).")
                except Exception as e:
                    messages.error(request, f"Ocurrió un error al enviar los correos: {e}")
            else:
                messages.info(request, "No se seleccionaron instructores con email válido para enviar correos.")

            return redirect('administracion:correo') # Redirige a la misma página o a otra
    else:
        form = EmailInstructoresForm()

    return render(request, 'administracion/correo.html', {'form': form})


