"""
Formularios para los usuarios
"""

# Django
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

# Modelos
from administracion.models import Alumno, Dojo

# Obtiene la clase del modelo de usuario que está configurado
# como el modelo de usuario personalizado en la aplicación
User = get_user_model()
class CreaUsuarioForm(forms.Form):
    """
    Formulario para la creación de un usuario
    """

    
class UsuarioSelectDojoForm(forms.Form):
    """Formulario para asistencia al curso"""

    # Corre electrónico del usuario
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control mt-3 mb-3'}),
        required=True,
        label="Correo electrónico"
    )
    # Selecciona el dojo al que pertenece el usuario
    dojo = forms.ModelChoiceField(
        queryset=Dojo.objects.all().order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control mt-3'}),
        required=True,
        empty_label="Selecciona tu Dojo",
        label="Dojo al que Perteneces"
    )

class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulario para solicitar un reinicio de contraseña:
    Valida email, nombre, apellidos y dojo para verificar identidad sin exponer
    datos de existencia a atacantes (OWASP User Enumeration Prevention).
    """

    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control mt-1 mb-4'}),
        required=True,
        label="Correo electrónico"
    )
    nombre = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control mt-1 mb-4'}),
        required=True,
        label="Nombre"
    )
    apellidos = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control mt-1 mb-4'}),
        required=True,
        label="Apellidos"
    )
    dojo = forms.ModelChoiceField(
        queryset=Dojo.objects.all().order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-select mt-1 mb-4'}),
        required=True,
        empty_label="Dojo al que perteneces",
        label="Dojo al que perteneces"
    )

    def get_users(self, email):
        """
        Filtra usuarios activos que coincidan con el email Y con los datos del alumno (nombre, apellidos, dojo).
        Si los datos no coinciden exactamente, no envía el correo pero tampoco filtra errores detallados.
        """
        active_users = super().get_users(email)
        nombre = self.cleaned_data.get('nombre', '').strip().lower()
        apellidos = self.cleaned_data.get('apellidos', '').strip().lower()
        dojo = self.cleaned_data.get('dojo')

        valid_users = []
        for user in active_users:
            try:
                alumno = Alumno.objects.select_related('dojo').get(usuario=user)
                if (alumno.nombre.strip().lower() == nombre and
                    alumno.apellidos.strip().lower() == apellidos and
                    alumno.dojo == dojo):
                    valid_users.append(user)
            except Alumno.DoesNotExist:
                if user.externo:
                    valid_users.append(user)

        return valid_users

