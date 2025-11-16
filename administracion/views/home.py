""" Vistas de la app administracion """

# Python
import datetime
import json

# Django

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.db.models import Count

# App administracion
from administracion.models import Alumno, Cursillo, Dojo, Actividad

@login_required
def home(request):
    """
    Home de la aplicación

    Devolvemos datos globales
    - El total de cinturones negros, dojos, cursillos tanto nacionales como internacionales
    - La cantidad de alumnos por danes
    """

    hoy = datetime.date.today()
    actividades = Actividad.objects.filter(fecha__gte=hoy).order_by('fecha')
    cn = Alumno.objects.all().count()
    cursos = Cursillo.objects.all().count()
    nacional = Cursillo.objects.filter(pais='España').count()
    internacional = Cursillo.objects.filter(internacional=True).count()
    extranjero = Cursillo.objects.exclude(pais='España').count()
    dojos = Dojo.objects.all().count()
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
        'dojos': dojos,
        'hoy': hoy,
        'actividades': actividades,
        'data_json': data_json,
    })