""" Vistas de la app administracion """

# Python
import datetime
import json

# Django
from django.db.models.query import QuerySet
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView, ListView, DetailView, CreateView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings

# App administracion
from .models import Alumno, Cursillo, Dojo, Peticion, Examen

# Utilidades
from .utils import envio_correo, enviar_correo_html

@login_required
def home(request):
    """
    Home de la aplicación

    Devolvemos datos globales
    - El total de cinturones negros, dojos, cursillos tanto nacionales como internacionales
    - La cantidad de alumnos por danes
    """
    cn = Alumno.objects.all().count()
    cursos = Cursillo.objects.all().count()
    nacional = Cursillo.objects.filter(pais='España').count()
    internacional = Cursillo.objects.filter(internacional=True).count()
    extranjero = Cursillo.objects.exclude(pais='España').count()
    # peticiones = Peticion.objects.filter(finalizada=False).count()
    dojos = Dojo.objects.all().count()
    hoy = datetime.date.today()
    data = Alumno.objects.values('grado').annotate(total=Count('id')).order_by('grado')
    labels = [item['grado'] for item in data]
    values = [item['total'] for item in data]
    data_json = json.dumps({
        'labels': labels,
        'values': values,
        'titulo': 'Número de alumnos por grado',
    })

    return render(request, 'administracion/home.html', {
        'cn': cn,
        'cursos': cursos,
        'nacional': nacional,
        'internacional': internacional,
        'extranjero': extranjero,
        # 'peticiones': peticiones,
        'dojos': dojos,
        'hoy': hoy,
        'data_json': data_json,
        # 'usuario_foto': usuario_foto.foto,
    })

class AlumnosView(LoginRequiredMixin, ListView):
    """
    Vista de alumnos por grado
    """
    model = Alumno
    template_name = 'administracion/alumnos.html'
    context_object_name = 'alumnos'
    # paginate_by = 10


    def get_queryset(self):
        """
        Define la consulta para obtener los alumnos por grado.
        Filtra por el grado obtenido en los parametros de la url
        Ordena los resultados
        """

        # Obtiene el valor de 'grado' de los argumentos de la URL (kwargs)
        # Si no se pasa 'grado' en la URL, usa 1 como valor predeterminado.
        grado = self.kwargs.get('grado', 1)
        queryset = super().get_queryset().filter(grado=grado).order_by('dojo', 'apellidos')
        # Alternativamente, podrías escribirlo sin llamar a super() aquí:
        #queryset = Alumno.objects.filter(grado=grado).order_by('dojo', 'apellidos')

        return queryset


    def get_context_data(self, **kwargs):
        """
        Obtenemos los datos de los cintos negros para hacer el grafico de barras

        Returns:
            El número de cintos negros por grado
        """
        context = super().get_context_data(**kwargs)
        grado = self.kwargs.get('grado', 1)
        context['grado'] = grado

        # Obtenemos los datos para hacer el gráfico de barras
        data = Alumno.objects.values('grado').annotate(total=Count('id')).order_by('grado')

        labels = [item['grado'] for item in data]
        values = [item['total'] for item in data]
        data_json = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': 'Número de alumnos por grado',})
        context['data_json'] = data_json

        # Obtenemos la cantidad de cintos negros en la consulta
        if self.context_object_name in context:
            context['cantidad'] = context[self.context_object_name].count()
        else:
            context['cantidad'] = self.get_queryset().count()

        context['grados_posibles'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        return context

class AlumnoDetailView(LoginRequiredMixin, DetailView):
    """
    Muestra los detalles de un alumno específico.
    Los exámenes que ha realizado y el tiempo que ha estado en cada grado
    """
    model = Alumno
    template_name = 'administracion/detalle_alumno.html' # Crea esta plantilla
    context_object_name = 'alumno' # Nombre del objeto en la plantilla detalle

    def get_context_data(self, **kwargs):
        """
        Calculamos los eventos en los que se ha examinado y los años en cada grado
        """
        # Creamos las variables locales para los calculos
        anios = list()
        examen = list()
        hoy = datetime.date.today()
        # Llama a la implementación de la base para obtener el contexto inicial
        context = super(AlumnoDetailView, self).get_context_data(**kwargs)
        # Obtiene el objeto alumno actual
        alumno = self.get_object()

        # Obtenemos la lista de examenes de ese alumno
        examenes = Examen.objects.filter(alumno=alumno.id)

        for idx, exam in enumerate(examenes):
            examen.append(str(exam.grado) + " DAN")
            print(exam.evento.evento)
            print(exam.evento.fecha)
            # Verificamos si el indica actual es el último de la lista
            if idx == len(examenes) - 1:
                anios.append(hoy.year - exam.evento.fecha.year)
            else:
                anios.append(examenes[idx + 1].evento.fecha.year - exam.evento.fecha.year)

        context['examen'] = examen
        context['examenes'] = examenes
        context['hoy'] = hoy

        context['anios'] = anios
        context['total_anios'] = sum(anios)

        # Calculamos la edad del alumno
        if alumno.fecha_nacimiento is None:
            edad_a = 0
            edad_b = 0
        else:
            edad = hoy - alumno.fecha_nacimiento
            edad = divmod(edad.days, 365)
            edad_a = edad[0]
            edad_b = edad[1]
        context['edad'] = edad_a

        # Preparamos el gráfico
        data_json = json.dumps({
            'labels': examen,
            'values': anios,
            'titulo': 'Años en cada grado',
        })
        context['data_json'] = data_json

        return context

class DojosView(LoginRequiredMixin, ListView):
    """Listado de gimnasios de la asociación"""

    template_name = 'administracion/dojos.html'
    model = Dojo
    context_object_name = 'dojos'


    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()
        return context

class DojoDetailView(LoginRequiredMixin, DetailView):
    """
    Detalle de un Dojo
    """

    template_name = 'administracion/detalle_dojo.html'
    model = Dojo
    context_object_name = 'dojo'

    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        # Obtenemos el objeto dojo actual
        dojo_actual = self.get_object()
        # Obtenemos los datos del instructor y lo añadimos al contexto
        instructor_obj = Alumno.objects.select_related('usuario').filter(
            dojo=dojo_actual,
            instructor=True
        ).first()
        context['instructor'] = instructor_obj
        print(instructor_obj)

        # Obtenemos todos los cintos negros del dojo
        cintos_negros_dojo_obj = Alumno.objects.filter(dojo = dojo_actual, instructor=False).order_by("apellidos")
        context['cintos_negros_dojo'] = cintos_negros_dojo_obj

        # Obtenemos los cintos negros por grado
        # 1. Filtra por el dojo actual y que no sean instructores
        # 2. Agrupa por 'grado' usando values('grado')
        # 3. Cuenta los alumnos en cada grupo ('grado')
        # 4. Ordena por 'grado'
        cintos_negros_por_grado = Alumno.objects.filter(
            dojo=dojo_actual,
            instructor=False
        ).values('grado').annotate(
            total=Count('id')
        ).order_by('grado')
        # Extracción de Datos
        labels = [item['grado'] for item in cintos_negros_por_grado]
        values = [item['total'] for item in cintos_negros_por_grado]
        context['cinturon_negro_data_json'] = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': f'Alumnos por Grado en {dojo_actual.nombre}', # Título dinámico
        })
        context['total_cintos_negros'] = sum(values)

        # Obtenemos las peticiones pendientes por dojo
        peticiones = Peticion.objects.filter(dojo=dojo_actual, finalizada=False)
        numero_peticiones = peticiones.count()
        context['peticiones'] = peticiones
        context['numero_peticiones'] = numero_peticiones

        return context

class CursillosView(LoginRequiredMixin, ListView):
    """Listado de gimnasios de la asociación"""

    template_name = 'administracion/cursillos.html'
    model = Cursillo
    context_object_name = 'cursillos'


    def get_context_data(self, **kwargs):
        """
        Obtenemos la cantidad de dojos asociados para añadirlo al contexto
        """
        context = super().get_context_data(**kwargs)
        context['cantidad'] = self.get_queryset().count()
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
        # Obtenemos todos los asistentes a un cursillo
        # asistentes_obj = Cursillo.objects.select_related('alumnos').get(pk=curso_actual.id)
        context["asistentes"] = curso_actual.alumnos.all().order_by('apellidos')

        return context


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
class PeticionCreateView(LoginRequiredMixin, CreateView):
    """
    Introducimos los datos de una petición nueva en la BBDD
    """

    model = Peticion
    fields = ['titulo', 'tipo', 'dojo', 'descripcion']

class PeticionView(LoginRequiredMixin, TemplateView):
    """
    Vista para realizar peticiones
    Procesa el formulario de petición y crea la petición en la BBDD.
    Obtiene los datos de la petición para mostrarlos en el template
    Si el usuario es staff, obtiene todas las peticiones pendiente
    Si el usuario es instructor, obtiene las peticiones pendientes del dojo actual
    """
    template_name = 'administracion/peticiones.html'
    context_object_name = 'peticion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtenemos los datos del usuario logado
        user = self.request.user

        # Inicializamos las variables
        # Esto garantiza que estas variables de contexto siempre existan,
        # incluso si el usuario no está asociado a un Dojo.
        dojo_usuario = None
        peticiones_pendientes = Peticion.objects.none()

        # Obtenemos los datos deldojo y sus peticiones pendientes
        if user.is_authenticated:
            try:
                # Obtiene una instancia de alumno para el usuario actual
                alumno = Alumno.objects.select_related('dojo').get(usuario=user)
                dojo_usuario = alumno.dojo
                # Obtenemos todas las peticiones pendientes si el usuario es staff o superuser
                # En caso sontrario las del dojo actual
                if user.is_staff or user.is_superuser:
                    peticiones_pendientes = Peticion.objects.filter(
                        finalizada=False
                    ).order_by('-fecha')
                else:
                    peticiones_pendientes = Peticion.objects.filter(
                        dojo=dojo_usuario,
                        finalizada=False
                    ).order_by('-fecha')
            except Alumno.DoesNotExist: # pylint: disable=no-member
                pass

        # Almacena el objeto dojo y sus peticiones pendientes
        context ['dojo_usuario'] = dojo_usuario
        context['peticiones_pendientes'] = peticiones_pendientes
        context['user'] = user

        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de petición y crea la petición en la BBDD.
        """
        # Obtenemos las variables del formulario
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo')
        dojo_id = request.POST.get('dojo')
        descripcion = request.POST.get('descripcion')
        destinatario = settings.EMAIL_DEFAULT_STAFF

        # Validar que los campos no estén vacíos
        if not all([titulo, tipo, dojo_id, descripcion]):
            return render(request, self.template_name, {
                'error': 'Por favor, complete todos los campos.',
                'dojos': Dojo.objects.all()
            })

        # Obtenemos las plantillas HTML y TXT para el correo
        template_name_html='administracion/emails/notificacion_peticion.html',
        template_name_texto='administracion/emails/notificacion_peticion.txt',

        # Obtener el Dojo
        dojo = get_object_or_404(Dojo, pk=dojo_id)

        # Crear la petición
        Peticion.objects.create(
            titulo=titulo,
            tipo=tipo,
            dojo=dojo,
            descripcion=descripcion
        )
        # Convertimos el objeto creado un un diccionario
        peticion = {
            'titulo': titulo,
            'dojo': dojo.nombre,
            'email': request.user.email,
            'descripcion': descripcion,
        }
        contexto = {
            'peticion': peticion,
        }

        # Enviamos el correo electrónico
        enviar_correo_html(
            asunto = f'Nueva petición de {dojo.nombre}: {titulo}',
            template_name_html=template_name_html,
            template_name_texto=template_name_texto,
            contexto = contexto,
            destinatarios = destinatario,
        )

        return redirect('administracion:peticiones')


class PeticionAnularView(LoginRequiredMixin, View):
    """
    Anula una petición
    """

    def post(self, request, pk):
        peticion = get_object_or_404(Peticion, pk=pk)
        peticion.finalizada = True
        peticion.save()

        return redirect('administracion:peticiones')

class CorreoView(LoginRequiredMixin, TemplateView):
    """Envío de correo a instructores"""
    template_name = 'administracion/correo.html'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtenemos todos los instructores y sus correos
        instructores = Alumno.objects.select_related('usuario').filter(instructor=True).order_by('apellidos')
        context['instructores'] = instructores

        return context

@login_required
def Cursillos_View(request):
    cursillo = Cursillo.objects.all().order_by('-fecha')
    hoy = datetime.date.today()
    return render(request, 'administracion/cursillos.html', {'cursillo': cursillo, 'hoy': hoy})