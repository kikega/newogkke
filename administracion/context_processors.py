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
            alumno_obj = Alumno.objects.select_related('usuario').get(usuario__email=request.user.email)
            context_data['usuario_foto'] = alumno_obj.foto
        except Alumno.DoesNotExist: # pylint: disable=no-member
            # Si no hay alumno asociado, usuario foto ya es None
            pass
        # Contar peticiones pendientes 
        peticiones_pendientes = Peticion.objects.filter(finalizada=False).count()
        context_data['peticiones'] = peticiones_pendientes

    return context_data
