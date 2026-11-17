"""
Los context processors en Django son funciones que toman el objeto request como argumento
 y devuelven un diccionario que se añade al contexto de la solicitud. Estos 
 procesadores permiten compartir datos globales, como configuraciones del sitio, 
 en todos los templates sin necesidad de pasarlos manualmente a través de cada vista.
"""
from django.core.cache import cache

from administracion.models import Peticion
from administracion.permissions import (
    es_alumno_solo_portal_dojo,
    es_usuario_juez_efimero,
    obtener_alumno_instructor,
    obtener_perfiles_alumno,
    obtener_tatamis_activos_juez,
    usuario_es_instructor_o_staff,
)


def common_navbar_context(request):
    """
    Añade información común para la barra de navegación y contexto multi-tenant de Dojo.
    """
    context_data = {
        'usuario_foto': None,
        'peticiones_totales': 0,
        'usuario_es_instructor': False,
        'usuario_es_global': False,
        'usuario_es_alumno_portal': False,
        'usuario_es_juez_tatami': False,
        'tatami_juez_activo': None,
        'usuario_dojo': None,
        'alumno_dan_actual': None,
        'alumno_color_actual': None,
        'current_dojo': getattr(request, 'current_dojo', None),
        'is_dojo_host': getattr(request, 'is_dojo_host', False),
    }

    if request.user.is_authenticated:
        if es_usuario_juez_efimero(request.user):
            context_data['usuario_es_juez_tatami'] = True
            context_data['tatami_juez_activo'] = obtener_tatamis_activos_juez(request.user).first()
            return context_data

        alumno_dan, alumno_color = obtener_perfiles_alumno(request.user)
        es_instructor = obtener_alumno_instructor(request.user) is not None
        es_global = usuario_es_instructor_o_staff(request.user)

        if alumno_dan:
            context_data['usuario_foto'] = alumno_dan.foto
            context_data['usuario_dojo'] = alumno_dan.dojo
            context_data['alumno_dan_actual'] = alumno_dan
        elif alumno_color:
            context_data['usuario_dojo'] = alumno_color.dojo
            context_data['alumno_color_actual'] = alumno_color

        context_data['usuario_es_instructor'] = es_instructor
        context_data['usuario_es_global'] = es_global
        context_data['usuario_es_alumno_portal'] = es_alumno_solo_portal_dojo(request.user)

        # Contar peticiones pendientes con caché (5 minutos)
        peticiones_totales = cache.get('peticiones_totales')
        if peticiones_totales is None:
            peticiones_totales = Peticion.objects.filter(finalizada=False).count()
            cache.set('peticiones_totales', peticiones_totales, 300)
        context_data['peticiones_totales'] = peticiones_totales

    return context_data
