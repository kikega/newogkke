"""
    Formularios
"""
# Django
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

# Modelos
from administracion.models import Alumno, Tablon, Actividad

class EmailInstructoresForm(forms.Form):
    """
    Formulario para la selección de instructores
    """

    # Filtra solo instructores y trae el usuario asociado
    # ModelMultipleChoiceField: Permite seleccionar múltiples objetos de un modelo.
    instructores = forms.ModelMultipleChoiceField(
        queryset=Alumno.objects.filter(instructor=True).select_related('usuario'),
        widget=FilteredSelectMultiple("Instructores", is_stacked=False),
        #label="Seleccionar Instructores",
        required=True,
        #help_text="Selecciona los instructores a los que deseas enviar el correo."(attrs={'class': 'form-control', 'rows': 5})
    )
    asunto = forms.CharField(
        label="Asunto del Correo",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}) # Bootstrap class opcional
    )
    mensaje = forms.CharField(
        label="Mensaje del Correo",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}) # Bootstrap class opcional
    )

    class Media:
        """
        Esta clase Media es CRUCIAL para que el widget funcione
        """
        css = {
            'all': ('/static/admin/css/widgets.css',), # Ajusta la ruta si es necesario
        }
        js = ('/admin/jsi18n/', '/static/admin/js/core.js', '/static/admin/js/SelectBox.js', '/static/admin/js/SelectFilter2.js')
        # Es importante que estas rutas sean correctas y accesibles.
        # /admin/jsi18n/ es generado por Django.
        # Los archivos .js y .css de admin/static/ deben ser servidos por tu servidor de estáticos.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Para que el queryset se evalúe dinámicamente si cambian los instructores (opcional)
        self.fields['instructores'].queryset = Alumno.objects.filter(instructor=True).select_related('usuario')
        # Personalizar el texto que se muestra en el widget para cada alumno
        self.fields['instructores'].label_from_instance = lambda obj: f"{obj.nombre} {obj.apellidos} ({obj.usuario.email if obj.usuario else 'Sin email'})"

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
        fields = ['titulo', 'descripcion', 'lugar', 'ciudad', 'provincia', 'pais', 'fecha']
        widgets = {
            'titulo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'descripcion': forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
            'fecha': forms.DateInput(attrs={"class": "form-control mt-2 mb-3", "type": "date"}),
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
        label="Información",
        widget=forms.FileInput(attrs={"class": "form-control mt-2 mb-3", "type": "file"}),
        required = False
    )


class TablonEditForm(forms.ModelForm):
    """Formulario para editar un anuncio en el tablón de anuncios de un dojo"""

    class Meta:
        model = Tablon
        fields = ['titulo', 'descripcion', 'lugar', 'informacion']
        widgets = {
            'titulo': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'descripcion': forms.Textarea(attrs={"class": "form-control mt-2 mb-3", "rows": 5}),
            'lugar': forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
            'informacion': forms.FileInput(attrs={"class": "form-control mt-2 mb-3", "type": "file"}),
        }


class InscripcionAlumnosForm(forms.Form):
    """
    Formulario para la inscripción de alumnos a un cursillo por parte de un instructor.
    """

    # ModelMultipleChoiceField permite seleccionar múltiples alumnos.
    alumnos = forms.ModelMultipleChoiceField(
        queryset=Alumno.objects.none(),  # El queryset se establecerá dinámicamente en __init__
        widget=FilteredSelectMultiple("Alumnos", is_stacked=False),
        label="Seleccionar Alumnos",
        required=False, # Puede que no se seleccione a nadie
        help_text="Selecciona los alumnos de tu dojo para inscribirlos al cursillo."
    )

    class Media:
        """
        Esta clase Media es CRUCIAL para que el widget FilteredSelectMultiple funcione.
        """
        css = {
            'all': ('/static/admin/css/widgets.css',),
        }
        js = ('/admin/jsi18n/', '/static/admin/js/core.js', '/static/admin/js/SelectBox.js', '/static/admin/js/SelectFilter2.js')

    def __init__(self, *args, **kwargs):
        # Extraemos los argumentos personalizados que pasaremos desde la vista
        # Extraemos el usuario (que debe ser un instructor) y el cursillo.
        user = kwargs.pop('user', None)
        cursillo = kwargs.pop('cursillo', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            try:
                # Obtenemos el queryset base: alumnos del dojo del instructor
                instructor = Alumno.objects.get(usuario=user)
                dojo_instructor = instructor.dojo
                alumnos_queryset = Alumno.objects.filter(
                    dojo=dojo_instructor,
                    instructor=False,
                    activo=True
                ).order_by('apellidos', 'nombre')

                self.fields['alumnos'].queryset = alumnos_queryset

                # Obtenemos los ID de los alumnos ya inscritos en el cursillo
                inscritos_ids = cursillo.alumnos.values_list('id', flat=True)

                # Le decimos al campo que su valor inical son los alumnos del dojo
                # que tambien se encuentran en la lista de inscritos
                self.fields['alumnos'].initial = alumnos_queryset.filter(id__in=inscritos_ids)     
                        
                # Personalizar el texto que se muestra en el widget para cada alumno
                self.fields['alumnos'].label_from_instance = lambda obj: f"{obj.apellidos}, {obj.nombre}"
            
            except Alumno.DoesNotExist:
                self.fields['alumnos'].queryset = Alumno.objects.none()
