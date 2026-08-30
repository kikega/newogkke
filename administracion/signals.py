"""
    Señales para el logging
"""

import logging
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from administracion.utils import get_client_ip

logger = logging.getLogger('access_logger')

@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):
    logger.info("LOGIN SUCCESS - %s - IP: %s", user.username, get_client_ip(request))

@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'UNKNOWN')
    logger.warning("LOGIN FAILED - %s - IP: %s", username, get_client_ip(request))


