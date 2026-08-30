"""
Vistas relacionadas con la gestión de los alumnos
"""

# Python
import datetime
import json

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Count

# App administracion
from administracion.models import Alumno, Examen

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
        Obtenemos los datos de los cintos negros para hacer el gráfico de barras completo
        """
        context = super().get_context_data(**kwargs)
        grado = self.kwargs.get('grado', 1)
        context['grado'] = grado

        # Obtenemos los datos completos del 1º al 10º DAN
        data = Alumno.objects.exclude(grado__isnull=True).values('grado').annotate(total=Count('id'))
        counts_by_grado = {item['grado']: item['total'] for item in data}
        labels = [f"{g}º DAN" for g in range(1, 11)]
        values = [counts_by_grado.get(g, 0) for g in range(1, 11)]

        data_json = json.dumps({
            'labels': labels,
            'values': values,
            'titulo': 'Número de alumnos por grado',
        })
        context['data_json'] = data_json

        if self.context_object_name in context:
            context['cantidad'] = context[self.context_object_name].count()
        else:
            context['cantidad'] = self.get_queryset().count()

        context['grados_posibles'] = list(range(1, 11))
        return context


class AlumnoDetailView(LoginRequiredMixin, DetailView):
    """
    Muestra los detalles de un alumno específico:
    Exámenes ordenados cronológicamente y tiempo de permanencia en cada grado.
    """
    model = Alumno
    template_name = 'administracion/detalle_alumno.html'
    context_object_name = 'alumno'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.get_object()
        hoy = datetime.date.today()

        # Obtenemos la lista de exámenes de ese alumno ordenados por fecha
        examenes = list(Examen.objects.filter(alumno=alumno).select_related('evento').order_by('evento__fecha'))

        anios = []
        examen = []
        for idx, exam in enumerate(examenes):
            examen.append(f"{exam.grado}º DAN")
            if idx == len(examenes) - 1:
                anios_grado = max(0, hoy.year - exam.evento.fecha.year)
            else:
                siguiente_fecha = examenes[idx + 1].evento.fecha
                anios_grado = max(0, siguiente_fecha.year - exam.evento.fecha.year)
            anios.append(anios_grado)

        context['examen'] = examen
        context['examenes'] = examenes
        context['hoy'] = hoy
        context['anios'] = anios
        context['total_anios'] = sum(anios)
        context['examenes_anios'] = list(zip(examenes, anios))

        # Cálculo exacto de la edad
        if alumno.fecha_nacimiento:
            edad = hoy.year - alumno.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (alumno.fecha_nacimiento.month, alumno.fecha_nacimiento.day)
            )
        else:
            edad = 0
        context['edad'] = edad

        # Datos del gráfico de años en cada grado
        data_json = json.dumps({
            'labels': examen,
            'values': anios,
            'titulo': 'Años en cada grado',
        })
        context['data_json'] = data_json

        return context


