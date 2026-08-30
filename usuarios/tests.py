from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from administracion.models import Dojo, Alumno
from usuarios.forms import CustomPasswordResetForm

User = get_user_model()

class UsuariosSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.create(
            nombre="Dojo Usuarios Test",
            direccion="Calle Test 12",
            poblacion="Madrid",
            provincia="Madrid",
            codigo_postal="28001"
        )
        self.user = User.objects.create_user(
            email="alumno@test.com",
            password="OldPassword123!"
        )
        self.alumno = Alumno.objects.create(
            usuario=self.user,
            nombre="Juan",
            apellidos="Pérez",
            dojo=self.dojo,
            instructor=False,
            grado=1
        )

    def test_custom_password_reset_form_filters_matching_user(self):
        """Verifica que CustomPasswordResetForm filtra los usuarios válidos correctamente."""
        # Datos correctos
        form = CustomPasswordResetForm(data={
            'email': 'alumno@test.com',
            'nombre': 'Juan',
            'apellidos': 'Pérez',
            'dojo': self.dojo.pk
        })
        self.assertTrue(form.is_valid())
        users = list(form.get_users('alumno@test.com'))
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], self.user)

        # Datos incorrectos (dojo o nombre falso)
        other_dojo = Dojo.objects.create(nombre="Otro Dojo", direccion="Dir", poblacion="Mad", provincia="Mad", codigo_postal="28002")
        form_wrong = CustomPasswordResetForm(data={
            'email': 'alumno@test.com',
            'nombre': 'Juan',
            'apellidos': 'Pérez',
            'dojo': other_dojo.pk
        })
        self.assertTrue(form_wrong.is_valid())
        users_wrong = list(form_wrong.get_users('alumno@test.com'))
        self.assertEqual(len(users_wrong), 0)

    def test_cambio_password_view_authenticated(self):
        """Verifica cambio de contraseña con credenciales válidas y protección contra claves faltantes."""
        self.client.force_login(self.user)
        
        # Petición POST con campos vacíos no debe arrojar MultiValueDictKeyError (código 500)
        response = self.client.post(reverse('cambio_password'), {})
        self.assertEqual(response.status_code, 200) # Renderiza cambio_password.html con error descriptivo

        # Petición con contraseña correcta
        response = self.client.post(reverse('cambio_password'), {
            'old_password': 'OldPassword123!',
            'new_password': 'NewPassword123!',
            'new_password_conf': 'NewPassword123!'
        })
        self.assertEqual(response.status_code, 302) # Redirige al login / inicio
