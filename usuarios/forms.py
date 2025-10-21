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
        - email: debe existir en la BD
        - nombre/apellidos: opcionalmente podríamos validarlos también
        - dojo: relacionado con el usuario
    """

    # Correo electrónico del usuario
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
        #label="Dojo al que Perteneces"
    )

    def clean_email(self):
        """
        Validamos que el email existe en la base de datos de usuarios
        """

        email = self.cleaned_data['email']

        # Si no existe la cuenta, lanzamos una excepción
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No existe una cuenta asociada a este correo electrónico")
        return email
    
    def clean(self):
        """
        Validacion cruzada, comprobamos que nombre, apellidos y dojo, correspondan al usuario
        """
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        nombre = cleaned_data.get('nombre')
        apellidos = cleaned_data.get('apellidos')
        dojo = cleaned_data.get('dojo')

        if email and nombre and apellidos and dojo:
            # Obtenemos los datos de alumno relativos al usuario
            alumno = Alumno.objects.select_related("usuario").get(usuario__email=email)
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return cleaned_data
            if alumno.nombre.lower() != nombre.lower() and alumno.apellidos.lower() != apellidos.lower():
                self.add_error(None, "Los datos de nombre y apellidos no coinciden con el usuario")
            if alumno.dojo != dojo:
                self.add_error(None, "El usuario no pertenece al dojo seleccionado")
            return cleaned_data

        return cleaned_data
            
