"""
    Utilidades comúnes de administración
"""
# logging nos permite un registro de eventos más robusto
import logging

# Correo
from smtplib import SMTPException
from email.mime.image import MIMEImage

# Parser HTML
from html.parser import HTMLParser
import io

# Expresiones regulares

# Django
from django.core.mail import send_mail, EmailMultiAlternatives, send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib import messages

import re

logger = logging.getLogger(__name__)

class StripTags(HTMLParser):
    """Clase para eliminar tags HTML"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = io.StringIO()

    def handle_data(self, data):
        self.text.write(data)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    """
    Funcion que llama a la clase StripTags para eliminar tags HTML
    """
    s = StripTags()
    s.feed(html)
    return s.get_data()


def envio_correo(asunto, mensaje, destinatario, mensaje_html=None):
    """
    Envía un correo electrónico a un destinatario o a una lista de destinatarios
    """

    try:
        # Asegurarse de que destinatario sea una lista o tupla de strings
        if isinstance(destinatario, str):
            lista_destinatarios = [destinatario]
        else:
            lista_destinatarios = destinatario

        logger.info("Intentando enviar correo: Asunto = %s, Destinatarios= %s", asunto, lista_destinatarios)
        send_mail(
            subject = asunto,
            message = mensaje,
            from_email = settings.EMAIL_HOST_USER,
            recipient_list = lista_destinatarios,
            html_message = mensaje_html,
            fail_silently = False,
        )
        logger.info("Correo enviado exitosamente: Asunto = %s, Destinatarios = %s", asunto, lista_destinatarios)
        return True
    except SMTPException as e:
        logger.error("Error SMTP al enviar correo: Asunto = %s, Destinatarios = %s, Error = %s", asunto, lista_destinatarios, e)
        return False


def enviar_correo_html(asunto, template_name_html, template_name_texto, contexto, destinatarios, remitente=None):
    """
    Envía un correo utilizando plantillas HTML y de texto plano.
    - asunto: Asunto del correo.
    - template_name_html: Ruta a la plantilla HTML (ej: 'emails/nueva_peticion.html').
    - template_name_texto: Ruta a la plantilla de texto plano (ej: 'emails/nueva_peticion.txt').
    - contexto: Diccionario con los datos para renderizar las plantillas.
    - destinatarios: Lista de direcciones de email.
    - remitente: Email del remitente (opcional, usa settings.DEFAULT_FROM_EMAIL por defecto).
    """

    # Obtenemos el path relativo y el absoluto de la imagen a incrustar
    # Y lo añadimos al contexto
    contexto_completo = contexto.copy()
    path_relativo_logo = 'img/logo.png'
    # path_absoluto_logo = settings.BASE_DIR / path_relativo_logo
    # id_imagen_cid = path_relativo_logo.split('/')[-1]
    # contexto_completo['logo_cid'] = id_imagen_cid

    # print(path_relativo_logo, path_absoluto_logo, id_imagen_cid)

    if path_relativo_logo:
        path_absoluto_logo = finders.find(path_relativo_logo)
        if path_absoluto_logo:
            id_imagen_cid = path_relativo_logo.split('/')[-1].replace('.', '_') # Hacerlo más único y sin puntos
            contexto_completo['logo_cid'] = id_imagen_cid

    if not destinatarios:
        return False, "No se proporcionaron destinatarios."

    if not remitente:
        remitente = settings.EMAIL_HOST_USER

    try:
        logger.info("Intentando enviar correo: Asunto = %s, Destinatarios= %s", asunto, destinatarios)
        # Renderizar la plantilla HTML
        html_content = render_to_string(template_name_html, contexto_completo)

        # Renderizar la plantilla de texto plano
        # Si no se proporciona una plantilla de texto, se puede intentar generar a partir del HTML
        if template_name_texto:
            text_content = render_to_string(template_name_texto, contexto)
        else:
            text_content = strip_tags(html_content) # Opción básica si no hay plantilla de texto

        # Crear el objeto EmailMultiAlternatives
        msg = EmailMultiAlternatives(asunto, text_content, remitente, destinatarios)
        msg.attach_alternative(html_content, "text/html") # Adjuntar la versión HTML

        if path_absoluto_logo and id_imagen_cid:
            try:
                with open(path_absoluto_logo, 'rb') as f:
                    mime_image = MIMEImage(f.read())
                    mime_image.add_header('Content-ID', f'<{id_imagen_cid}>') # El < > es importante
                    msg.attach(mime_image)
            except IOError as e:
                logger.error("Error al leer o adjuntar imagen: %s", e)

        # Enviar el correo
        msg.send(fail_silently=False)
        logger.info("Correo enviado exitosamente: Asunto = %s, Destinatarios = %s", asunto, destinatarios)
        return True, f"Correo enviado exitosamente a {len(destinatarios)} destinatario(s)."

    except Exception as e:
        # Imprimir el error 'e' para depuración
        logger.error("Error al enviar correo con plantilla HTML: %s", e, exc_info=True)
        return False, f"Ocurrió un error al enviar el correo: {e}"


def validar_cadena(cadena):
    """
    Chequea si una cadena contiene caracteres especiales
    Devuelve False si contiene caracteres especiales
    """

    patron_variable = re.compile(r'[a-zA-Z0-9ñáéíóúÑÁÉÍÓÚ\s]*$')
    resultado_match = patron_variable.match(cadena)

    if resultado_match: # Usa el resultado del match que debería funcionar
        return True
    else:
        return False

def is_ajax(request):
    """
        Función de ayuda para detectar peticiones AJAX
    """
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def get_client_ip(request):
    """
    Obtiene la dirección IP del cliente de forma segura.
    Prioriza X-Forwarded-For si existe y está detrás de proxy, o REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def invitar_o_vincular_usuario_alumno(alumno_obj, email, request):
    """
    Crea o actualiza la cuenta de Usuario para un Alumno (DAN) o AlumnoColor (Kyu mayor de edad)
    y envía por correo electrónico el enlace seguro para establecer su contraseña e iniciar sesión
    en el portal de su Dojo.
    Bloquea estrictamente la creación de cuentas para menores de 18 años.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.tokens import default_token_generator
    from django.core.exceptions import ValidationError
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    from administracion.models import Alumno, AlumnoColor

    if getattr(alumno_obj, 'es_menor_edad', False):
        raise ValidationError(
            "Los menores de 18 años no tienen acceso a la aplicación; el instructor del Dojo es el encargado de realizar sus gestiones."
        )

    email_clean = (email or "").strip().lower()
    if not email_clean:
        raise ValidationError("Debes proporcionar un correo electrónico válido.")

    User = get_user_model()
    current_user = alumno_obj.usuario

    existing_user = User.objects.filter(email__iexact=email_clean).first()
    if existing_user and (not current_user or existing_user.pk != current_user.pk):
        tiene_otro_dan = Alumno.objects.filter(usuario=existing_user).exclude(
            pk=alumno_obj.pk if isinstance(alumno_obj, Alumno) else None
        ).exists()
        tiene_otro_color = AlumnoColor.objects.filter(usuario=existing_user).exclude(
            pk=alumno_obj.pk if isinstance(alumno_obj, AlumnoColor) else None
        ).exists()
        if tiene_otro_dan or tiene_otro_color or existing_user.is_staff or existing_user.is_superuser:
            raise ValidationError("Ese correo electrónico ya está asignado a otro usuario del sistema.")
        user = existing_user
        user.first_name = alumno_obj.nombre
        user.last_name = alumno_obj.apellidos
        user.is_active = True
        user.save()
    elif current_user:
        user = current_user
        user.email = email_clean
        user.username = email_clean
        user.first_name = alumno_obj.nombre
        user.last_name = alumno_obj.apellidos
        user.is_active = True
        user.save()
    else:
        user = User(
            email=email_clean,
            username=email_clean,
            first_name=alumno_obj.nombre,
            last_name=alumno_obj.apellidos,
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

    if alumno_obj.usuario_id != user.pk:
        alumno_obj.usuario = user
        alumno_obj.save()

    # Generar enlace de activación / creación de contraseña
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    domain = request.get_host() if request else getattr(settings, 'DOJO_BASE_DOMAIN', 'ogkke.es')
    protocol = 'https' if (request and request.is_secure()) else 'http'

    context = {
        'email': user.email,
        'domain': domain,
        'site_name': 'OGKKE',
        'uid': uid,
        'user': user,
        'token': token,
        'protocol': protocol,
        'dojo': alumno_obj.dojo,
    }
    subject = f"Activación de acceso al Portal del Dojo {alumno_obj.dojo.nombre} · OGKKE"
    html_body = render_to_string('usuarios/emails/email_reset_password.html', context)
    text_body = strip_tags(html_body)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'ogkke@egalvez.es')

    msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)

    return user
