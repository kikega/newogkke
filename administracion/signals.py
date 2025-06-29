"""
    Señales para el logging
"""

import logging
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger('access_logger')

@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):
    logger.info(f"LOGIN SUCCESS - {user.username} - IP: {get_ip(request)}")

@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'UNKNOWN')
    logger.warning(f"LOGIN FAILED - {username} - IP: {get_ip(request)}")

def get_ip(request):
    return request.META.get('REMOTE_ADDR', '')
