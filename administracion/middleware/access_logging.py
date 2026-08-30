import logging
from datetime import datetime
from administracion.utils import get_client_ip

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
        response = self.get_response(request)
        return response
