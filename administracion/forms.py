"""
    Formularios
"""
# Django
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

# Modelos
from administracion.models import Alumno

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
        widget = forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
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
        required = True
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
    )
    ciudad = forms.CharField(
        label="Ciudad",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
    )
    provincia = forms.CharField(
        label="Provincia",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
    )
    pais = forms.CharField(
        label="País",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control mt-2 mb-3",}),
    )
