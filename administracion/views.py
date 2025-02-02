""" Vistas de la app administracion """

# Python
import datetime
import json

# Django
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count

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
    peticiones = Peticion.objects.filter(finalizada=False).count()
    dojos = Dojo.objects.all().count()
    hoy = datetime.date.today()
    data = Alumno.objects.values('grado').annotate(total=Count('id')).order_by('grado')
    labels = [item['grado'] for item in data]
    values = [item['total'] for item in data]
    data_json = json.dumps({
        'labels': labels,
        'values': values,
        'titulo': 'Alumnos por grado',
    })

    danes = list()
    for i in range(1, 11):
        i = Alumno.objects.filter(grado=i).count()
        danes.append(i)
  
    return render(request, 'administracion/home.html', {
        'cn': cn,
        'danes': danes,
        'cursos': cursos,
        'nacional': nacional,
        'internacional': internacional,
        'extranjero': extranjero,
        'peticiones': peticiones,
        'dojos': dojos,
        'hoy': hoy,
        'data_json': data_json,
    })
