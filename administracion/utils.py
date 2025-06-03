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
import re

# Django
from django.core.mail import send_mail, EmailMultiAlternatives, send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib import messages

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
                print(f"Error al leer o adjuntar imagen: {e}")

        # Enviar el correo
        msg.send(fail_silently=False)
        logger.info("Correo enviado exitosamente: Asunto = %s, Destinatarios = %s", asunto, destinatarios)
        return True, f"Correo enviado exitosamente a {len(destinatarios)} destinatario(s)."

    except Exception as e:
        # Imprimir el error 'e' para depuración
        print(f"Error al enviar correo con plantilla HTML: {e}")
        # Para desarrollo
        # logger.error(f"Error al enviar correo con plantilla HTML: {e}", exc_info=True) # Para producción
        return False, f"Ocurrió un error al enviar el correo: {e}"


def validar_cadena(cadena):
    """
    Chequea si una cadena contiene caracteres especiales
    Devuelve False si contiene caracteres especiales
    """

    patron = re.compile(r'[^a-zA-Z0-9\s]*$')

    if patron.match(cadena):
        return True
    else:
        return False

