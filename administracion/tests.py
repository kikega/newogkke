from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group
from administracion.models import Dojo, Alumno, Tablon, Actividad, Peticion, Cursillo
import datetime

User = get_user_model()

class AdministracionSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Crear grupos
        self.instructor_group, _ = Group.objects.get_or_create(name='Instructor')
        
        # Crear Dojo
        self.dojo = Dojo.objects.create(
            nombre="Dojo Test",
            direccion="Calle Falsa 123",
            poblacion="Madrid",
            provincia="Madrid",
            codigo_postal="28001"
        )
        
        # Crear otro Dojo para validaciones cruzadas
        self.other_dojo = Dojo.objects.create(
            nombre="Dojo Secundario",
            direccion="Avenida Principal 456",
            poblacion="Madrid",
            provincia="Madrid",
            codigo_postal="28002"
        )

        # Crear usuarios
        self.superuser = User.objects.create_superuser(
            email="superuser@test.com",
            password="SecurePassword123!"
        )
        
        self.staff_user = User.objects.create_user(
            email="staff@test.com",
            password="SecurePassword123!",
            is_staff=True
        )
        
        self.instructor_user = User.objects.create_user(
            email="instructor@test.com",
            password="SecurePassword123!"
        )
        self.instructor_alumno = Alumno.objects.create(
            usuario=self.instructor_user,
            nombre="Instructor",
            apellidos="Test",
            dojo=self.dojo,
            instructor=True,
            grado=1
        )
        self.instructor_user.groups.add(self.instructor_group)

        self.regular_user = User.objects.create_user(
            email="regular@test.com",
            password="SecurePassword123!"
        )
        self.regular_alumno = Alumno.objects.create(
            usuario=self.regular_user,
            nombre="Alumno",
            apellidos="Test",
            dojo=self.dojo,
            instructor=False,
            grado=1
        )

        # Cursillo
        self.cursillo = Cursillo.objects.create(
            evento="Curso Nacional",
            descripcion="Curso de Karate",
            lugar="Polideportivo",
            ciudad="Madrid",
            fecha=datetime.date.today()
        )

        # Actividad
        self.actividad = Actividad.objects.create(
            tipo="Entrenamiento",
            titulo="Entrenamiento Especial",
            descripcion="Entrenamiento intensivo",
            fecha=datetime.date.today(),
            lugar="Central",
            ciudad="Madrid"
        )

        # Tablon
        self.tablon = Tablon.objects.create(
            dojo=self.dojo,
            tipo="Aviso",
            titulo="Aviso Importante",
            descripcion="Cierre festivos",
            fecha=datetime.date.today(),
            lugar="Tablon Central"
        )

        # Peticion
        self.peticion = Peticion.objects.create(
            dojo=self.dojo,
            titulo="Cambio horario",
            tipo="m",
            descripcion="Modificar hora",
            finalizada=False
        )

    def test_database_engine_setting(self):
        """Verifica que el motor de base de datos usa la configuración correcta de Django 6."""
        # Durante los tests, el motor se configura a sqlite3
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
        # Pero en el archivo settings.py está configurado a postgresql
        import pathlib
        settings_path = pathlib.Path(settings.BASE_DIR) / 'ogkke' / 'settings.py'
        content = settings_path.read_text()
        self.assertIn("'ENGINE': 'django.db.backends.postgresql'", content)

    def test_error_view_no_crash(self):
        """Verifica que la vista de error no genera UnboundLocalError para códigos distintos a 403."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('administracion:errores', kwargs={'error_code': 404}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("El recurso solicitado no existe o no se encontró.", response.context['error_message'])

    def test_view_does_not_crash_without_alumno_profile(self):
        """Verifica que las vistas principales de administrador no crashean si el staff no posee perfil de alumno."""
        self.client.force_login(self.staff_user)
        
        # Peticiones View
        response = self.client.get(reverse('administracion:peticiones'))
        self.assertEqual(response.status_code, 200)
        
        # Tablon View
        response = self.client.get(reverse('administracion:tablon'))
        self.assertEqual(response.status_code, 200)
        
        # Cursillo Detail View
        response = self.client.get(reverse('administracion:cursillo_detalle', kwargs={'pk': self.cursillo.pk}))
        self.assertEqual(response.status_code, 200)

    def test_actividades_authorization_restrictions(self):
        """Verifica restricciones de acceso en actividades globales."""
        # Usuario normal intentando crear actividad
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse('administracion:actividades'), {
            'tipo': 'Entrenamiento',
            'titulo': 'Hacked',
            'fecha': '2026-06-20',
            'lugar': 'Malicioso',
            'ciudad': 'Madrid'
        })
        self.assertEqual(response.status_code, 403) # Forbidden / PermissionDenied

        # Usuario normal intentando editar actividad
        response = self.client.post(reverse('administracion:editar_actividad', kwargs={'pk': self.actividad.pk}), {
            'titulo': 'Hacked'
        })
        self.assertEqual(response.status_code, 403)

        # Usuario normal intentando eliminar actividad
        response = self.client.post(reverse('administracion:eliminar_actividad', kwargs={'pk': self.actividad.pk}))
        self.assertEqual(response.status_code, 403)

        # Administrador sí puede realizar estas acciones
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('administracion:actividades'), {
            'tipo': 'Entrenamiento',
            'titulo': 'Nuevo entrenamiento',
            'fecha': '2026-06-20',
            'lugar': 'Dojo central',
            'ciudad': 'Madrid'
        })
        self.assertEqual(response.status_code, 302) # Redirect to index

    def test_tablon_authorization_restrictions(self):
        """Verifica que solo instructores de su dojo o administradores editan anuncios."""
        # Alumno normal intentando editar anuncio del dojo
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse('administracion:editar_tablon', kwargs={'pk': self.tablon.pk}), {
            'titulo': 'Hacked'
        })
        self.assertEqual(response.status_code, 403)

        # Instructor de otro dojo intentando publicar o editar
        other_instructor_user = User.objects.create_user(email="other_instructor@test.com", password="Password123!")
        Alumno.objects.create(
            usuario=other_instructor_user,
            nombre="Other",
            apellidos="Instructor",
            dojo=self.other_dojo,
            instructor=True
        )
        self.client.force_login(other_instructor_user)
        # Intentando publicar en dojo equivocado
        response = self.client.post(reverse('administracion:tablon'), {
            'dojo': self.dojo.id,
            'titulo': 'Hacked',
            'fecha': '2026-06-20',
            'tipo': 'Aviso',
            'lugar': 'Central'
        })
        self.assertEqual(response.status_code, 403)

        # Instructor correcto sí puede publicar en su dojo
        self.client.force_login(self.instructor_user)
        response = self.client.post(reverse('administracion:tablon'), {
            'dojo': self.dojo.id,
            'titulo': 'Anuncio Real',
            'fecha': '2026-06-20',
            'tipo': 'Aviso',
            'lugar': 'Dojo'
        })
        self.assertEqual(response.status_code, 302)

    def test_peticiones_authorization_restrictions(self):
        """Verifica restricciones de creación y anulación de peticiones."""
        # Alumno normal no puede crear peticiones
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse('administracion:peticiones'), {
            'dojo': self.dojo.id,
            'titulo': 'Hacked',
            'descripcion': 'Hacked description'
        })
        self.assertEqual(response.status_code, 403)

        # Alumno normal no puede anular peticiones
        response = self.client.post(reverse('administracion:peticiones_anular', kwargs={'pk': self.peticion.pk}), {
            'action': 'finalizar'
        })
        self.assertEqual(response.status_code, 403)

        # Instructor correcto sí puede anular su petición (borrar)
        self.client.force_login(self.instructor_user)
        response = self.client.post(reverse('administracion:peticiones_anular', kwargs={'pk': self.peticion.pk}), {
            'action': 'borrar'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Peticion.objects.filter(pk=self.peticion.pk).exists())
