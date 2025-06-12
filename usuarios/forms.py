"""
Formularios para los usuarios
"""

# Django
from django import forms
from administracion.models import Alumno, Dojo


class CreaUsuarioForm(forms.Form):
    """
    Formulario para la creación de un usuario
    """

    
class UsuarioSelectDojoForm(forms.Form):
    """Formulario para asistencia al curso"""

    # Selecciona el dojo al que pertenece el usuario
    dojo = forms.ModelChoiceField(
        queryset=Dojo.objects.all().order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control mt-2'}),
        required=True,
        empty_label="Selecciona tu Dojo",
        label="Dojo al que Perteneces"
    )
