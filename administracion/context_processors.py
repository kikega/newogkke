"""
Los context processors en Django son funciones que toman el objeto request como argumento
 y devuelven un diccionario que se añade al contexto de la solicitud. Estos 
 procesadores permiten compartir datos globales, como configuraciones del sitio, 
 en todos los templates sin necesidad de pasarlos manualmente a través de cada vista.
"""
from django.core.cache import cache

# Importamos los modelos de Alumno y Peticion
from administracion.models import Alumno, Peticion

def common_navbar_context(request):
    """
    Añade información común para la barra de navegación al contexto.
    """
    context_data = {
        'usuario_foto': None,
        'peticiones_totales': 0,
        'usuario_es_instructor': False,
    }

    # Obtenemos la foto y estado de instructor del usuario que esta logado
    if request.user.is_authenticated:
        es_instructor = request.user.groups.filter(name='Instructor').exists()
        try:
            alumno_obj = Alumno.objects.select_related('usuario').get(usuario=request.user)
            context_data['usuario_foto'] = alumno_obj.foto
            es_instructor = es_instructor or alumno_obj.instructor
        except Alumno.DoesNotExist: # pylint: disable=no-member
            pass
        context_data['usuario_es_instructor'] = es_instructor

        # Contar peticiones pendientes con caché (5 minutos)
        peticiones_totales = cache.get('peticiones_totales')
        if peticiones_totales is None:
            peticiones_totales = Peticion.objects.filter(finalizada=False).count()
            cache.set('peticiones_totales', peticiones_totales, 300)
        context_data['peticiones_totales'] = peticiones_totales

    return context_data
