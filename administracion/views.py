""" Vistas de la app administracion """

# Python
import datetime
import json

# Django
from django.db.models.query import QuerySet
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db.models import Count
from django.shortcuts import get_object_or_404

# App administracion
from .models import Alumno, Cursillo, Dojo, Peticion, Examen

# Para envío de correo
from django.core.mail import send_mail
from django.conf import settings
from smtplib import SMTPException

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
        Calculamos los eventos en los que se haexaminado y los años en cada grado
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
        if alumno.fecha_nacimiento == None:
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
    context_object_name = 'dojo'


@login_required
def Cursillos_View(request):
    cursillo = Cursillo.objects.all().order_by('-fecha')
    hoy = datetime.date.today()
    return render(request, 'administracion/cursillos.html', {'cursillo': cursillo, 'hoy': hoy})