# Importamos los modelos de Alumno y Peticion
from administracion.models import Alumno, Peticion

def common_navbar_context(request):
    """
    Añade información común para la barra de navegación al contexto.
    """
    context_data = {
        'usuario_foto': None,
        'peticiones': 0,
    }

    # Obtenemos la foto del usuario que esta logado
    if request.user.is_authenticated:
        try:
            usuario_foto = Alumno.objects.select_related('usuario').get(usuario__email=request.user.email)
        except Alumno.DoesNotExist: # pylint: disable=no-member
            usuario_foto = None
        # Contar peticiones pendientes 
        peticiones_pendientes = Peticion.objects.filter(finalizada=False).count()
        context_data = {
            'usuario_foto': usuario_foto.foto,
            'peticiones': peticiones_pendientes,
        }

    return context_data
