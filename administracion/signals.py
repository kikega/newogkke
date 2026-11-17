"""
    Señales para el logging y sincronización automática de grupos de rol (Instructor)
"""

import logging
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from administracion.models import Alumno
from administracion.utils import get_client_ip

logger = logging.getLogger('access_logger')

@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):
    logger.info("LOGIN SUCCESS - %s - IP: %s", user.username, get_client_ip(request))

@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'UNKNOWN')
    logger.warning("LOGIN FAILED - %s - IP: %s", username, get_client_ip(request))


@receiver(post_save, sender=Alumno)
def sync_instructor_group_on_alumno_save(sender, instance, **kwargs):
    """
    Sincroniza automáticamente la pertenencia al grupo 'Instructor' de Django
    con los campos instructor y activo del modelo Alumno.
    """
    if not instance.usuario_id:
        return
    instructor_group, _ = Group.objects.get_or_create(name='Instructor')
    if instance.instructor and instance.activo:
        instance.usuario.groups.add(instructor_group)
    else:
        instance.usuario.groups.remove(instructor_group)



