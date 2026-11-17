import logging
from datetime import datetime
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from administracion.utils import get_client_ip
from administracion.permissions import (
    es_usuario_juez_efimero,
    obtener_tatamis_activos_juez,
    verificar_vigencia_login_juez,
)

logger = logging.getLogger('access_logger')


class AccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else 'Anonymous'
        path = request.path
        method = request.method
        logger.info("%s - %s - %s - %s %s", datetime.now(), ip, user, method, path)

        if request.user.is_authenticated and es_usuario_juez_efimero(request.user):
            permitido, _ = verificar_vigencia_login_juez(request.user)
            if not permitido:
                logout(request)
                return redirect('login')

            # Confinar al juez de tatami exclusivamente a las rutas de tatami, ayuda y logout
            rutas_permitidas_prefijos = (
                '/campeonatos/tatami/',
                '/campeonatos/ayuda/',
                '/usuarios/logout',
                '/static/',
                '/media/',
            )
            if path == '/':
                tatami_activo = obtener_tatamis_activos_juez(request.user).first()
                if tatami_activo:
                    return redirect(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami_activo.id}))
            elif not path.startswith(rutas_permitidas_prefijos):
                raise PermissionDenied(
                    "Los usuarios operadores de Tatami tienen acceso exclusivo al panel de su Tatami asignado."
                )

        response = self.get_response(request)
        return response
