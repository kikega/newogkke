""" Vistas de la app administracion """

# Python
import datetime
import json

# Django

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.db.models import Count, Q

# App administracion
from administracion.models import Alumno, Cursillo, Dojo, Actividad

@login_required
def home(request):
    """
    Home de la aplicación
    Devuelve datos globales agregados y mapa de alumnos por grado.
    """
    hoy = datetime.date.today()
    actividades = Actividad.objects.filter(fecha__gte=hoy).order_by('fecha')
    cn = Alumno.objects.count()
    dojos = Dojo.objects.count()

    # Consulta única agregada para métricas de cursillos
    cursillos_stats = Cursillo.objects.aggregate(
        total=Count('id'),
        nacional=Count('id', filter=Q(pais__iexact='España')),
        internacional=Count('id', filter=Q(internacional=True)),
        extranjero=Count('id', filter=~Q(pais__iexact='España'))
    )

    # Mapeo completo y sincronizado de 1º a 10º DAN
    data = Alumno.objects.exclude(grado__isnull=True).values('grado').annotate(total=Count('id'))
    counts_by_grado = {item['grado']: item['total'] for item in data}
    labels = [f"{g}º DAN" for g in range(1, 11)]
    values = [counts_by_grado.get(g, 0) for g in range(1, 11)]

    data_json = json.dumps({
        'labels': labels,
        'values': values,
        'titulo': 'Número de alumnos por grado',
    })

    return render(request, 'administracion/home.html', {
        'cn': cn,
        'cursos': cursillos_stats['total'] or 0,
        'nacional': cursillos_stats['nacional'] or 0,
        'internacional': cursillos_stats['internacional'] or 0,
        'extranjero': cursillos_stats['extranjero'] or 0,
        'dojos': dojos,
        'hoy': hoy,
        'actividades': actividades,
        'data_json': data_json,
    })