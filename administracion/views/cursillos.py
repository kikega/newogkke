"""
Vistas relacionadas con la gestión de cursillos
"""

# Python
import datetime
import json

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import View, TemplateView, ListView, DetailView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.http import FileResponse

# App administracion
from administracion.models import Alumno, Cursillo, Examen

# Utilidades
from administracion.utils import enviar_correo_html, validar_cadena

# Formularios
from administracion.forms import InscripcionAlumnosForm   

class CursillosView(LoginRequiredMixin, ListView):
    """Listado de cursillos realiozados"""

    template_name = 'administracion/cursillos.html'
    model = Cursillo
    context_object_name = 'cursillos'


    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()

        # Obtenemos la fecha actual
        hoy = datetime.date.today()
        context['hoy'] = hoy
        return context


class CursilloDetailView(LoginRequiredMixin, DetailView):
    """
    Obtenemos el detalle de cada cursillo
    Los alumnos que han asistido
    """

    model = Cursillo
    template_name = 'administracion/detalle_cursillo.html'
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_actual = self.get_object()

        # Obtenemos datos del usuario logado 
        user = self.request.user
        # Obtenemos datos del alumno para ver si ya está inscrito
        alumno = Alumno.objects.select_related('usuario').get(usuario=user)
        alumno_cursillo = curso_actual.alumnos.filter(pk=alumno.id).exists()
        context['alumno_cursillo_inscrito'] = alumno_cursillo

        # Obtenemos el dato si es instructor
        es_instructor = False
        if user.is_authenticated:
            es_instructor = user.groups.filter(name='instructor').exists()
        # Añades la variable booleana al contexto
        context['usuario_es_instructor'] = es_instructor

        # Obtenemos todos los asistentes a un cursillo
        # asistentes_obj = Cursillo.objects.select_related('alumnos').get(pk=curso_actual.id)
        context["asistentes"] = curso_actual.alumnos.all().order_by('apellidos')
        # Obtenemos la fecha actual
        context['hoy'] = datetime.date.today()

        return context


class CursoNuevoView(LoginRequiredMixin, ListView):
    """
    Creamos un curso nuevo
    """
    template_name = 'administracion/cursillos.html'
    model = Cursillo
    context_object_name = 'cursillos'

    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de seminarios realizados
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()

        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de creación de un nuevo curso
        """

        # Obtenemos los datos del formulario
        evento = request.POST.get('evento')
        descripcion = request.POST.get('descripcion')
        lugar = request.POST.get('lugar')
        pais = 'España' if request.POST.get('pais') == "" else request.POST.get("pais")
        ciudad = request.POST.get('ciudad')
        fecha = request.POST.get('fecha')
        internacional = True if request.POST.get('internacional') == 'on' else False
        examenes = True if request.POST.get('examenes') == 'on' else False
        if request.FILES.get('circular'):
            circular = request.FILES["circular"]
        else:
            circular = None

        # Validar que los campos que son obligatorios, no contengan caracteres especiales
        if not validar_cadena(evento):
            error_producido = 403
            return redirect ('administracion:errores', error_producido)

        if not validar_cadena(lugar):
            error_producido = 403
            return redirect ('administracion:errores', error_producido)

        if not validar_cadena(ciudad):
            error_producido = 403
            return redirect ('administracion:errores', error_producido)

        # Creamos el nuevo curso
        try:
            Cursillo.objects.get_or_create(
                evento = evento,
                descripcion = descripcion,
                lugar = lugar,
                pais = pais,
                ciudad = ciudad,
                fecha = fecha,
                internacional = internacional,
                examenes = examenes,
                circular = circular
            )
        except Exception as e:
            print(f'Ha habido un error: {e}')

        return redirect('administracion:cursillos')


class CursilloExaminaListView(LoginRequiredMixin, DetailView):
    """
    Listado de todos los que se examinan en un cursillo
    """

    model = Cursillo
    template_name = 'administracion/cursillo_examinan.html'
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso_actual = self.get_object()

        # Obtenemos todos los alumnos que se examinan en el cursillo
        context['examinan'] = Examen.objects.filter(evento=curso_actual).select_related('alumno').order_by('alumno__apellidos')
        context['curso'] = curso_actual
        print(curso_actual)

        return context


class CursilloEstadisticasView(LoginRequiredMixin, DetailView):
    """
    Obtiene las estadisticas de todos los cintos negros de cada Dojo que han asistido al cursillo
    """

    model = Cursillo
    template_name = "administracion/cursillo_estadisticas.html"
    context_object_name = 'cursillo'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        curso_actual = self.object
        context['curso'] = curso_actual

        asistentes_por_dojo = curso_actual.alumnos.values(
            'dojo__nombre'  # Agrupa por el nombre del Dojo
        ).annotate(
            total_asistentes=Count('id') # Cuenta los alumnos (id) en cada grupo de dojo
        ).order_by('-total_asistentes')
        context['estadisticas_asistentes_por_dojo'] = asistentes_por_dojo

        # Preparar datos para el gráfico
        labels_dojo = []
        values_asistentes = []

        for item in asistentes_por_dojo:
            labels_dojo.append(item['dojo__nombre'])
            values_asistentes.append(item['total_asistentes'])

        # Convertir a JSON para pasarlo a JavaScript en la plantilla
        context['asistentes_por_dojo'] = json.dumps({
            'labels': labels_dojo,
            'values': values_asistentes,
        })

        return context


class CursilloInscripcionInstructorView(LoginRequiredMixin, TemplateView):
    """
    Inscripción al cursillo.
    - Si el usuario es instructor/staff, muestra un formulario para inscribir a sus alumnos.
    - Si el usuario es un alumno normal, lo inscribe a él mismo directamente.
    """
    template_name = 'administracion/inscripcion_instructor.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Maneja la lógica de inscripción directa para no-instructores antes de
        llegar a los métodos GET o POST.
        """
        user = self.request.user
        cursillo = get_object_or_404(Cursillo, pk=self.kwargs['pk'])
        
        try:
            alumno = Alumno.objects.get(usuario=user)
        except Alumno.DoesNotExist:
            messages.error(request, "No tienes un perfil de alumno para inscribirte.")
            return redirect('administracion:cursillo_detalle', pk=cursillo.id)

        # Si el usuario no es instructor ni staff, se inscribe a sí mismo y se redirige.
        if not (user.is_staff or alumno.instructor):
            cursillo.alumnos.add(alumno)
            cursillo.save()
            messages.success(request, f"Te has inscrito correctamente en {cursillo.evento}.")
            return redirect('administracion:cursillo_detalle', pk=cursillo.id)
        
        # Si es instructor o staff, continúa con el flujo normal (GET o POST).
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Prepara el contexto para la plantilla, incluyendo el formulario.
        """
        context = super().get_context_data(**kwargs)
        context['cursillo'] = get_object_or_404(Cursillo, pk=self.kwargs['pk'])
        # Pasamos el usuario al formulario para que filtre por su dojo.
        context['form'] = InscripcionAlumnosForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de inscripción de alumnos.
        """
        cursillo = get_object_or_404(Cursillo, pk=self.kwargs['pk'])
        form = InscripcionAlumnosForm(request.POST, user=request.user)

        if form.is_valid():
            alumnos_a_inscribir = form.cleaned_data['alumnos']
            cursillo.alumnos.add(*alumnos_a_inscribir)
            messages.success(request, f"Se han inscrito {alumnos_a_inscribir.count()} alumno(s) correctamente.")
        else:
            messages.error(request, "Hubo un error con el formulario. Por favor, inténtalo de nuevo.")
        
        return redirect("administracion:cursillo_detalle", pk=cursillo.id)
    



@login_required
def descargar_circular(request, pk):
    cursillo = get_object_or_404(Cursillo, pk=pk)

    if cursillo.circular and hasattr(cursillo.circular, 'path'):
        # Obtener la ruta absoluta al archivo
        # cursillo.circular.path te da la ruta absoluta si MEDIA_ROOT está bien configurado
        circular_path = cursillo.circular.path
        # Abrir el archivo en modo binario para lectura
        response = FileResponse(open(circular_path, 'rb'), as_attachment=True, filename=cursillo.circular.name)
        # as_attachment=True: Fuerza la descarga.
        # filename=cursillo.circular.name: Sugiere el nombre original del archivo al navegador.
        # Django se encarga de las cabeceras Content-Type, Content-Disposition,
        if not settings.DEBUG: # Solo añadir en producción
            response['Connection'] = 'close'
        return response
    else:
        return redirect("administracion:error", error_code=404, error_message="No se encontró el archivo circular")

