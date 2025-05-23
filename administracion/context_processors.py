"""
Los context processors en Django son funciones que toman el objeto request como argumento
 y devuelven un diccionario que se añade al contexto de la solicitud. Estos 
 procesadores permiten compartir datos globales, como configuraciones del sitio, 
 en todos los templates sin necesidad de pasarlos manualmente a través de cada vista.
"""
# Importamos los modelos de Alumno y Peticion
from administracion.models import Alumno, Peticion

def common_navbar_context(request):
    """
    Añade información común para la barra de navegación al contexto.
    """
    context_data = {
        'usuario_foto': None,
        'peticiones_totales': 0,
    }

    # Obtenemos la foto del usuario que esta logado
    if request.user.is_authenticated:
        try:
            alumno_obj = Alumno.objects.select_related('usuario').get(usuario__email=request.user.email)
            context_data['usuario_foto'] = alumno_obj.foto
        except Alumno.DoesNotExist: # pylint: disable=no-member
            # Si no hay alumno asociado, usuario foto ya es None
            pass
        # Contar peticiones pendientes 
        peticiones_pendientes = Peticion.objects.filter(finalizada=False).count()
        context_data['peticiones_totales'] = peticiones_pendientes

    return context_data
