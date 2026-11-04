from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group
from administracion.models import Dojo, Alumno, Tablon, Actividad, Peticion, Cursillo, Examen, CargoDirectivo, MiembroDirectiva
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

    def test_cursillo_inscripcion_alumno_post(self):
        """Verifica inscripción y anulación directa de un alumno en un cursillo."""
        self.client.force_login(self.regular_user)
        url = reverse('administracion:cursillo_inscripcion_alumno', kwargs={'pk': self.cursillo.pk})

        # Inscribirse
        response = self.client.post(url, {'action': 'inscribir'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.cursillo.alumnos.filter(pk=self.regular_alumno.pk).exists())

        # Desinscribirse
        response = self.client.post(url, {'action': 'desinscribir'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.cursillo.alumnos.filter(pk=self.regular_alumno.pk).exists())

    def test_cursillo_inscripcion_instructor_authorization(self):
        """Verifica que solo instructores o staff pueden acceder a la gestión de inscripciones del dojo."""
        # Alumno normal es rechazado con 403
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('administracion:cursillo_inscripcion_instructor', kwargs={'pk': self.cursillo.pk}))
        self.assertEqual(response.status_code, 403)

        # Instructor puede acceder
        self.client.force_login(self.instructor_user)
        response = self.client.get(reverse('administracion:cursillo_inscripcion_instructor', kwargs={'pk': self.cursillo.pk}))
        self.assertEqual(response.status_code, 200)

    def test_home_and_alumnos_views_return_ok(self):
        """Verifica que las vistas de dashboard y alumnos calculan métricas sin errores."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cn', response.context)
        self.assertIn('cursos', response.context)

        response = self.client.get(reverse('administracion:alumnos'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grados_posibles', response.context)

    def test_actividad_creation_saves_tipo(self):
        """Verifica que al crear una actividad se guarda el campo tipo."""
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('administracion:actividades'), {
            'tipo': 'Seminario',
            'titulo': 'Seminario de Kata',
            'descripcion': 'Práctica avanzada',
            'fecha': '2026-11-15',
            'lugar': 'Polideportivo Municipal',
            'ciudad': 'Alicante',
            'provincia': 'Alicante',
            'pais': 'España'
        })
        self.assertEqual(response.status_code, 302)
        actividad_creada = Actividad.objects.get(titulo='Seminario de Kata')
        self.assertEqual(actividad_creada.tipo, 'Seminario')

    def test_navbar_context_instructor_flag(self):
        """Verifica que usuario_es_instructor está disponible globalmente para instructores."""
        self.client.force_login(self.instructor_user)
        response = self.client.get(reverse('home'))
        self.assertTrue(response.context['usuario_es_instructor'])

        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('home'))
        self.assertFalse(response.context['usuario_es_instructor'])

    def test_home_core_decoupled_from_tablon_and_dojo_links_tablon(self):
        """Verifica que la portada nacional ya no expone la pestaña del Tablón y que el Dojo enlaza su Tablón local."""
        self.client.force_login(self.regular_user)

        home_res = self.client.get(reverse('home'))
        self.assertEqual(home_res.status_code, 200)
        self.assertNotContains(home_res, 'Tablón Anuncios')
        self.assertContains(home_res, 'Próximas Actividades Oficiales')

        dojo_res = self.client.get(reverse('administracion:dojo_detalle', kwargs={'pk': self.dojo.pk}))
        self.assertEqual(dojo_res.status_code, 200)
        self.assertEqual(dojo_res.context['numero_anuncios_tablon'], 1)
        self.assertContains(dojo_res, f"?dojo={self.dojo.pk}")

        tablon_other = self.client.get(f"{reverse('administracion:tablon')}?dojo={self.other_dojo.pk}")
        self.assertEqual(tablon_other.status_code, 200)
        self.assertEqual(tablon_other.context['dojo_usuario'], self.other_dojo)
        self.assertEqual(tablon_other.context['tablon'].count(), 0)
        self.assertFalse(tablon_other.context['puede_gestionar_tablon'])

    def test_alumnos_htmx_partial_and_full_render(self):
        """Verifica carga completa y actualización parcial HTMX por grado DAN sin jQuery/DataTables."""
        nidan_user = User.objects.create_user(email="nidan@test.com", password="Password123!")
        Alumno.objects.create(
            usuario=nidan_user,
            nombre="Kenji",
            apellidos="Miyagi",
            dojo=self.dojo,
            grado=2,
        )
        self.client.force_login(self.regular_user)

        # Petición normal -> página completa con gráfico y tabla responsiva
        full_res = self.client.get(reverse('administracion:alumnos'))
        self.assertEqual(full_res.status_code, 200)
        self.assertTemplateUsed(full_res, 'administracion/alumnos.html')
        self.assertContains(full_res, 'window.OGKKECharts?.renderBarChart')
        self.assertContains(full_res, 'data-ogkke-table')
        self.assertNotContains(full_res, 'jquery')
        self.assertNotContains(full_res, 'dataTables')

        # Petición parcial HTMX -> solo el panel de grado 2º DAN
        htmx_res = self.client.get(
            reverse('administracion:alumnos_grado', kwargs={'grado': 2}),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(htmx_res.status_code, 200)
        self.assertTemplateUsed(htmx_res, 'administracion/partials/alumnos_grado_panel.html')
        self.assertTemplateNotUsed(htmx_res, 'administracion/alumnos.html')
        self.assertContains(htmx_res, 'data-selected-grado="2"')
        self.assertContains(htmx_res, 'Miyagi, Kenji')

        # Petición HTMX con HX-Boosted -> devuelve página completa
        boosted_res = self.client.get(
            reverse('administracion:alumnos_grado', kwargs={'grado': 2}),
            HTTP_HX_REQUEST='true',
            HTTP_HX_BOOSTED='true',
        )
        self.assertEqual(boosted_res.status_code, 200)
        self.assertTemplateUsed(boosted_res, 'administracion/alumnos.html')

    def test_phase2_tables_and_charts_views_render_cleanly(self):
        """Verifica que todas las vistas de listados, detalles y estadísticas de Fase 2 renderizan sin jQuery."""
        self.cursillo.examenes = True
        self.cursillo.save()
        self.cursillo.alumnos.add(self.regular_alumno)
        Examen.objects.create(alumno=self.regular_alumno, evento=self.cursillo, grado=1)

        self.client.force_login(self.regular_user)
        urls = [
            reverse('administracion:dojos'),
            reverse('administracion:dojo_detalle', kwargs={'pk': self.dojo.pk}),
            reverse('administracion:alumno_detalle', kwargs={'pk': self.regular_alumno.pk}),
            reverse('administracion:cursillos'),
            reverse('administracion:cursillo_detalle', kwargs={'pk': self.cursillo.pk}),
            reverse('administracion:cursillo_examinados', kwargs={'pk': self.cursillo.pk}),
            reverse('administracion:cursillo_estadisticas', kwargs={'pk': self.cursillo.pk}),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200)
                self.assertNotContains(res, 'jquery')
                self.assertNotContains(res, 'dataTables')

    def test_phase3_searchable_checklists_and_post_payloads(self):
        """Verifica que inscripcion_instructor y correo usan checklists táctiles sin SelectFilter2/jsi18n."""
        self.client.force_login(self.instructor_user)
        inscripcion_url = reverse('administracion:cursillo_inscripcion_instructor', kwargs={'pk': self.cursillo.pk})

        get_res = self.client.get(inscripcion_url)
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, 'data-ogkke-checklist')
        self.assertNotContains(get_res, 'SelectFilter2')
        self.assertNotContains(get_res, 'jsi18n')

        # Inscribir alumno mediante POST de checkboxes
        post_add = self.client.post(inscripcion_url, {'alumnos': [self.regular_alumno.pk]})
        self.assertEqual(post_add.status_code, 302)
        self.assertTrue(self.cursillo.alumnos.filter(pk=self.regular_alumno.pk).exists())

        # Desmarcar todos mediante POST vacío
        post_clear = self.client.post(inscripcion_url, {})
        self.assertEqual(post_clear.status_code, 302)
        self.assertFalse(self.cursillo.alumnos.filter(pk=self.regular_alumno.pk).exists())

        # Vista de correo a instructores para staff
        self.client.force_login(self.staff_user)
        correo_res = self.client.get(reverse('administracion:correo'))
        self.assertEqual(correo_res.status_code, 200)
        self.assertContains(correo_res, 'data-ogkke-checklist')
        self.assertNotContains(correo_res, 'SelectFilter2')
        self.assertNotContains(correo_res, 'jsi18n')

    def test_phase3_native_dialogs_rendered_on_core_views(self):
        """Verifica que las modales del Core se renderizan como <dialog> nativos accesibles."""
        # Alumno regular: modalCambioPassword + modalInscripcionAlumno
        self.client.force_login(self.regular_user)
        detalle_curso = self.client.get(reverse('administracion:cursillo_detalle', kwargs={'pk': self.cursillo.pk}))
        self.assertContains(detalle_curso, '<dialog class="ogkke-dialog" id="modalCambioPassword"')
        self.assertContains(detalle_curso, '<dialog class="ogkke-dialog" id="modalInscripcionAlumno"')
        self.assertContains(detalle_curso, 'command="show-modal"')

        # Instructor: diálogo de confirmación para eliminar petición sin onclick confirm()
        self.client.force_login(self.instructor_user)
        peticiones_res = self.client.get(reverse('administracion:peticiones'))
        self.assertContains(peticiones_res, '<dialog class="ogkke-dialog" id="modalConfirmarBorrarPeticion"')
        self.assertNotContains(peticiones_res, 'return confirm(')

        # Staff: modalCursoNuevo y modales de Actividades + AJAX de edición
        self.client.force_login(self.staff_user)
        cursillos_res = self.client.get(reverse('administracion:cursillos'))
        self.assertContains(cursillos_res, '<dialog class="ogkke-dialog ogkke-dialog-lg" id="modalCursoNuevo"')

        act_res = self.client.get(reverse('administracion:actividades'))
        self.assertContains(act_res, '<dialog class="ogkke-dialog ogkke-dialog-lg" id="modalActividadNueva"')
        self.assertContains(act_res, '<dialog class="ogkke-dialog" id="modalEliminarActividad"')

        ajax_edit = self.client.get(
            reverse('administracion:editar_actividad', kwargs={'pk': self.actividad.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(ajax_edit.status_code, 200)
        self.assertIn('commandfor="modalEditarActividad"', ajax_edit.json()['html_form'])

        # Vista pública de password_reset
        self.client.logout()
        reset_res = self.client.get(reverse('password_reset'))
        self.assertEqual(reset_res.status_code, 200)
        self.assertContains(reset_res, '<dialog class="ogkke-dialog" id="errorFormModal"')

    def test_phase4_alumno_profile_shogo_and_timeline(self):
        """Verifica insignias Shogo, enlace de salto accesible y lista semántica del timeline."""
        self.instructor_alumno.grado = 7
        self.instructor_alumno.rango = 'k'
        self.instructor_alumno.save()
        Examen.objects.create(alumno=self.instructor_alumno, evento=self.cursillo, grado=7)

        self.client.force_login(self.regular_user)
        res = self.client.get(reverse('administracion:alumno_detalle', kwargs={'pk': self.instructor_alumno.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'href="#main-content"')
        self.assertContains(res, 'budo-rank-badge')
        self.assertContains(res, 'Kyoshi')
        self.assertContains(res, '<ol class="timeline" role="list">')

    def test_phase4_directiva_and_error_accessibility(self):
        """Verifica organigrama sin estilos inline de dimensiones y botón accesible en error.html."""
        cargo_pres = CargoDirectivo.objects.create(nombre="Presidente", orden_jerarquico=1)
        cargo_sec = CargoDirectivo.objects.create(nombre="Secretario General", orden_jerarquico=2)
        MiembroDirectiva.objects.create(cargo=cargo_pres, nombre_externo="Taro", apellidos_externo="Chojun", orden=1)
        MiembroDirectiva.objects.create(cargo=cargo_sec, alumno=self.instructor_alumno, orden=2)

        self.client.force_login(self.regular_user)
        dir_res = self.client.get(reverse('administracion:directiva'))
        self.assertEqual(dir_res.status_code, 200)
        self.assertContains(dir_res, 'president-card')
        self.assertContains(dir_res, 'Taro Chojun')
        self.assertNotContains(dir_res, 'style="width:')

        err_res = self.client.get(reverse('administracion:errores', kwargs={'error_code': 404}))
        self.assertEqual(err_res.status_code, 200)
        self.assertContains(err_res, 'data-history-back')
        self.assertNotContains(err_res, 'onclick=')




