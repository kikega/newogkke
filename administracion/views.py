""" Vistas de la app administracion """

# Python
import datetime
import json

# Django
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, View
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

    # try:
    #     usuario_foto = Alumno.objects.select_related('usuario').get(usuario__email=request.user.email)
    # except Alumno.DoesNotExist: # pylint: disable=no-member
    #     usuario_foto = None

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

class Alumnos_View(LoginRequiredMixin, ListView):
    """
    Vista de alumnos
    """
    model = Alumno
    template_name = 'administracion/alumnos.html'
    context_object_name = 'alumnos'
    paginate_by = 10

    
    def get_context_data(self, **kwargs):
        """
        Obtenemos los datos de los cintos negros para hacer el grafico de barras

        Returns:
            El número de cintos negros por grado
        """
        context = super().get_context_data(**kwargs)
        # try:
        #     usuario_foto = Alumno.objects.select_related('usuario').get(usuario__email=self.request.user.email)
        # except Alumno.DoesNotExist: # pylint: disable=no-member
        #     usuario_foto = None
        data = Alumno.objects.values('grado').annotate(total=Count('id')).order_by('grado')
        labels = [item['grado'] for item in data]
        values = [item['total'] for item in data]
        data_json = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': 'Número de alumnos por grado',})
        context = {
            # 'usuario_foto': usuario_foto.foto,
            'data_json': data_json
        }
        return context
    

class Dojos_View(LoginRequiredMixin, ListView):
    """Listado de gimnasios de la asociación"""
    template_name = 'dojos.html'
    model = Dojo
    context_object_name = 'dojo'