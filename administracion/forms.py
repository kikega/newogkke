"""
    Formularios
"""
# Django
from django import forms
from django.core.validators import FileExtensionValidator

# Modelos
from administracion.models import Alumno, Cursillo, Tablon, Actividad

class EmailInstructoresForm(forms.Form):
    """
    Formulario para la selección de instructores y envío de comunicado por correo.
    """

    instructores = forms.ModelMultipleChoiceField(
        queryset=Alumno.objects.filter(instructor=True).select_related('usuario', 'dojo'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input ogkke-check-input'}),
        label="Destinatarios (Instructores)",
        required=True,
        help_text="Selecciona uno o varios instructores a los que deseas enviar el comunicado."
    )
    asunto = forms.CharField(
        label="Asunto del correo",
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Convocatoria próxima reunión técnica',
            'required': True,
        })
    )
    mensaje = forms.CharField(
        label="Mensaje del correo",
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Escribe aquí el contenido del mensaje...',
            'required': True,
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructores'].queryset = (
            Alumno.objects.filter(instructor=True)
            .select_related('usuario', 'dojo')
            .order_by('apellidos', 'nombre')
        )
        self.fields['instructores'].label_from_instance = (
            lambda obj: (
                f"{obj.apellidos}, {obj.nombre} · "
                f"{obj.dojo.nombre if obj.dojo else 'Sin dojo'} "
                f"({obj.usuario.email if obj.usuario and obj.usuario.email else 'Sin email'})"
            )
        )

class ActividadNuevaForm(forms.Form):
    """
    Formulario para la creción de una nueva actividad
    """

    tipo = forms.CharField(
        max_length=50,
        label = "Tipo de actividad",
        widget = forms.TextInput(attrs={"class": "form-control mt-2 mb-3","id": "tipoActividad"}),
        required = True
    )
    titulo = forms.CharField(
        max_length=250,
        label = "Título",
        widget = forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = True
    )
    descripcion = forms.CharField(
        label = "Descripción",
        widget = forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
        required = False
    )

    fecha = forms.DateField(
        label = "Fecha",
        widget = forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}),
        required = True
    )
    lugar = forms.CharField(
        label="Lugar",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = True
    )
    ciudad = forms.CharField(
        label="Ciudad",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = True
    )
    provincia = forms.CharField(
        label="Provincia",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = False
    )
    pais = forms.CharField(
        label="País",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = False
    )

class ActividadEditForm(forms.ModelForm):
    """Formulario para editar una actividad"""

    class Meta:
        model = Actividad
        fields = ['tipo', 'titulo', 'descripcion', 'lugar', 'ciudad', 'provincia', 'pais', 'fecha']
        widgets = {
            'tipo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3"}),
            'titulo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'descripcion': forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
            'fecha': forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}, format='%Y-%m-%d'),
            'lugar': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'ciudad': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'provincia': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'pais': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        }

class TablonNuevoForm(forms.Form):
    """
    Formulario para crear un nuevo anuncio en el tablón
    """

    tipo = forms.CharField(
        max_length=50,
        label = "Tipo de actividad",
        widget = forms.TextInput(attrs={"class": "form-control mt-2 mb-3","id": "tipoActividad"}),
        required = True
    )
    titulo = forms.CharField(
        max_length=250,
        label = "Título",
        widget = forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = True
    )
    descripcion = forms.CharField(
        label = "Descripción",
        widget = forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
        required = False
    )
    fecha = forms.DateField(
        label = "Fecha",
        widget = forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}),
        required = True
    )
    lugar = forms.CharField(
        label="Lugar",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
        required = True
    )
    informacion = forms.FileField(
        label="Información (PDF)",
        widget=forms.FileInput(attrs={"class": "form-control mt-2 mb-3", "type": "file", "accept": ".pdf"}),
        validators=[FileExtensionValidator(['pdf'])],
        required = False
    )


class TablonEditForm(forms.ModelForm):
    """Formulario para editar un anuncio en el tablón de anuncios de un dojo"""

    class Meta:
        model = Tablon
        fields = ['tipo', 'titulo', 'descripcion', 'fecha', 'lugar', 'informacion']
        widgets = {
            'tipo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'titulo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'descripcion': forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
            'fecha': forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}, format='%Y-%m-%d'),
            'lugar': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'informacion': forms.FileInput(attrs={"class": "form-control mt-2 mb-3", "type": "file", "accept": ".pdf"}),
        }


class CursoForm(forms.ModelForm):
    """Formulario para crear/editar un cursillo"""

    class Meta:
        model = Cursillo
        fields = ['evento', 'descripcion', 'lugar', 'ciudad', 'pais', 'fecha', 'internacional', 'examenes', 'circular']
        widgets = {
            'evento': forms.TextInput(attrs={"class": "form-control mt-2 mb-3"}),
            'descripcion': forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 4}),
            'lugar': forms.TextInput(attrs={"class": "form-control mt-2 mb-3"}),
            'ciudad': forms.TextInput(attrs={"class": "form-control mt-2 mb-3"}),
            'pais': forms.TextInput(attrs={"class": "form-control mt-2 mb-3"}),
            'fecha': forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}),
            'internacional': forms.CheckboxInput(attrs={"class": "form-check-input"}),
            'examenes': forms.CheckboxInput(attrs={"class": "form-check-input"}),
            'circular': forms.FileInput(attrs={"class": "form-control mt-2 mb-3", "accept": ".pdf"}),
        }
        labels = {
            'evento': 'Nombre del evento',
            'descripcion': 'Descripción',
            'lugar': 'Lugar',
            'ciudad': 'Ciudad',
            'pais': 'País',
            'fecha': 'Fecha',
            'internacional': '¿Es internacional?',
            'examenes': '¿Hay exámenes?',
            'circular': 'Circular (PDF)',
        }


class InscripcionAlumnosForm(forms.Form):
    """
    Formulario para la inscripción de alumnos a un cursillo por parte de un instructor.
    """

    alumnos = forms.ModelMultipleChoiceField(
        queryset=Alumno.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input ogkke-check-input'}),
        label="Alumnos inscritos en el cursillo",
        required=False,
        help_text="Marca los alumnos que asistirán al cursillo y desmarca quienes causen baja."
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        cursillo = kwargs.pop('cursillo', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            if user.is_staff or user.is_superuser:
                alumnos_queryset = Alumno.objects.filter(
                    instructor=False,
                    activo=True
                ).select_related('dojo').order_by('dojo__nombre', 'apellidos', 'nombre')

                self.fields['alumnos'].queryset = alumnos_queryset
                inscritos_ids = cursillo.alumnos.values_list('id', flat=True)
                self.fields['alumnos'].initial = alumnos_queryset.filter(id__in=inscritos_ids)
                self.fields['alumnos'].label_from_instance = (
                    lambda obj: (
                        f"[{obj.dojo.nombre}] {obj.apellidos}, {obj.nombre}"
                        + (f" · {obj.grado}º DAN" if obj.grado else "")
                    )
                )
            else:
                try:
                    instructor = Alumno.objects.get(usuario=user)
                    dojo_instructor = instructor.dojo
                    alumnos_queryset = Alumno.objects.filter(
                        dojo=dojo_instructor,
                        instructor=False,
                        activo=True
                    ).order_by('apellidos', 'nombre')

                    self.fields['alumnos'].queryset = alumnos_queryset
                    inscritos_ids = cursillo.alumnos.values_list('id', flat=True)
                    self.fields['alumnos'].initial = alumnos_queryset.filter(id__in=inscritos_ids)
                    self.fields['alumnos'].label_from_instance = (
                        lambda obj: (
                            f"{obj.apellidos}, {obj.nombre}"
                            + (f" · {obj.grado}º DAN" if obj.grado else "")
                        )
                    )
                except Alumno.DoesNotExist:
                    self.fields['alumnos'].queryset = Alumno.objects.none()
