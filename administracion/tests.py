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
        """Verifica que las vistas de dashboard y alumnos calculan métricas sin errores para usuarios globales y redirigen a alumnos regulares."""
        self.client.force_login(self.instructor_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cn', response.context)
        self.assertIn('cursos', response.context)

        response = self.client.get(reverse('administracion:alumnos'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grados_posibles', response.context)

        # Un alumno regular en cambio es redirigido desde / directo al portal de su Dojo
        self.client.force_login(self.regular_user)
        reg_home = self.client.get(reverse('home'))
        self.assertEqual(reg_home.status_code, 302)
        self.assertEqual(reg_home.url, reverse('administracion:dojo_portal', kwargs={'slug': self.dojo.slug}))

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
        response = self.client.get(reverse('administracion:dojo_portal', kwargs={'slug': self.dojo.slug}))
        self.assertFalse(response.context['usuario_es_instructor'])
        self.assertTrue(response.context['usuario_es_alumno_portal'])

    def test_home_core_decoupled_from_tablon_and_dojo_links_tablon(self):
        """Verifica que la portada nacional ya no expone la pestaña del Tablón y que el Dojo enlaza su Tablón local."""
        self.client.force_login(self.instructor_user)

        home_res = self.client.get(reverse('home'))
        self.assertEqual(home_res.status_code, 200)
        self.assertNotContains(home_res, 'Tablón Anuncios')
        self.assertContains(home_res, 'Próximas Actividades Oficiales')

        dojo_res = self.client.get(reverse('administracion:dojo_detalle', kwargs={'pk': self.dojo.pk}))
        self.assertEqual(dojo_res.status_code, 200)
        self.assertEqual(dojo_res.context['numero_anuncios_particulares_tablon'], 1)
        self.assertEqual(dojo_res.context['numero_anuncios_tablon'], 2)
        self.assertContains(dojo_res, f"?dojo={self.dojo.pk}")

        tablon_other = self.client.get(f"{reverse('administracion:tablon')}?dojo={self.other_dojo.pk}")
        self.assertEqual(tablon_other.status_code, 200)
        self.assertEqual(tablon_other.context['dojo_usuario'], self.other_dojo)
        self.assertEqual(tablon_other.context['tablon_particulares'].count(), 0)
        self.assertEqual(tablon_other.context['tablon'].count(), 1)
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
        self.client.force_login(self.instructor_user)

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

        self.client.force_login(self.instructor_user)
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

        self.client.force_login(self.instructor_user)
        dir_res = self.client.get(reverse('administracion:directiva'))
        self.assertEqual(dir_res.status_code, 200)
        self.assertContains(dir_res, 'president-card')
        self.assertContains(dir_res, 'Taro Chojun')
        self.assertNotContains(dir_res, 'style="width:')

        err_res = self.client.get(reverse('administracion:errores', kwargs={'error_code': 404}))
        self.assertEqual(err_res.status_code, 200)
        self.assertContains(err_res, 'data-history-back')
        self.assertNotContains(err_res, 'onclick=')

    def test_dojo_slug_and_custom_domain_normalization_and_scoped_manager(self):
        """Verifica generación de slug único, normalización de dominio propio y aislamiento DojoScopedManager."""
        self.assertEqual(self.dojo.slug, "dojo-test")
        self.assertEqual(self.other_dojo.slug, "dojo-secundario")

        duplicate = Dojo.objects.create(
            nombre="Dojo Test",
            direccion="Otra Calle 1",
            poblacion="Valencia",
            provincia="Valencia",
            codigo_postal="46001",
            dominio_personalizado="https://WWW.KarateValencia.es:8443/inicio",
        )
        self.assertEqual(duplicate.slug, "dojo-test-2")
        self.assertEqual(duplicate.dominio_personalizado, "karatevalencia.es")
        self.assertEqual(duplicate.dominio_principal, "karatevalencia.es")

        # DojoScopedManager filtra estrictamente por dojo
        self.assertEqual(Tablon.objects.for_dojo(self.dojo).count(), 1)
        self.assertEqual(Tablon.objects.for_dojo(self.other_dojo).count(), 0)
        self.assertEqual(Tablon.objects.for_dojo(None).count(), 0)

    def test_dojo_portal_routing_by_path_subdomain_and_custom_domain(self):
        """Verifica que el portal del Dojo responde por ruta /dojo/<slug>/, subdominio y dominio propio."""
        self.dojo.dominio_personalizado = "karatebudokan.es"
        self.dojo.color_primario = "#b91c1c"
        self.dojo.lema = "Camino de la mano vacía"
        self.dojo.horario_resumen = "Lunes y Miércoles 20:00 - 21:30"
        self.dojo.save()

        # 1. Acceso público anónimo por ruta directa /dojo/<slug>/
        public_res = self.client.get(reverse('dojo_portal_public', kwargs={'slug': self.dojo.slug}))
        self.assertEqual(public_res.status_code, 200)
        self.assertTemplateUsed(public_res, 'administracion/dojo_portal.html')
        self.assertContains(public_res, 'Dojo Oficial Afiliado a OGKKE')
        self.assertContains(public_res, 'Camino de la mano vacía')
        self.assertContains(public_res, 'data-dojo-theme="custom"')
        self.assertContains(public_res, '--dojo-accent: #b91c1c')

        # 2. Acceso por subdominio automático (dojo-test.ogkke.es) en la raíz /
        sub_res = self.client.get('/', HTTP_HOST='dojo-test.ogkke.es')
        self.assertEqual(sub_res.status_code, 200)
        self.assertTemplateUsed(sub_res, 'administracion/dojo_portal.html')
        self.assertEqual(sub_res.context['dojo'], self.dojo)

        # 3. Acceso por dominio propio (karatebudokan.es) en la raíz / sin reiniciar servidor
        custom_res = self.client.get('/', HTTP_HOST='karatebudokan.es')
        self.assertEqual(custom_res.status_code, 200)
        self.assertTemplateUsed(custom_res, 'administracion/dojo_portal.html')
        self.assertEqual(custom_res.context['dojo'], self.dojo)

    def test_dojo_portal_configuration_authorization_and_update(self):
        """Verifica que solo el instructor titular del Dojo o el Staff pueden configurar su portal y dominio."""
        config_url = reverse('administracion:dojo_portal_config', kwargs={'slug': self.dojo.slug})

        # Alumno normal recibe 403
        self.client.force_login(self.regular_user)
        forbidden_res = self.client.post(config_url, {
            'sitio_activo': 'on',
            'dominio_personalizado': 'pirata.es',
            'color_primario': '#123456',
        })
        self.assertEqual(forbidden_res.status_code, 403)

        # Instructor titular sí puede actualizar su configuración
        self.client.force_login(self.instructor_user)
        ok_res = self.client.post(config_url, {
            'sitio_activo': 'on',
            'dominio_personalizado': 'https://www.DojoTestMadrid.es/',
            'color_primario': '#1d4ed8',
            'lema': 'Goju-Ryu Madrid',
            'descripcion_publica': 'Dojo tradicional en el centro de Madrid.',
            'horario_resumen': 'Martes y Jueves 19:30 - 21:00',
            'telefono_contacto': '+34 600 111 222',
            'email_contacto': 'contacto@dojotestmadrid.es',
        })
        self.assertEqual(ok_res.status_code, 302)
        self.dojo.refresh_from_db()
        self.assertEqual(self.dojo.dominio_personalizado, 'dojotestmadrid.es')
        self.assertEqual(self.dojo.color_primario, '#1d4ed8')
        self.assertEqual(self.dojo.lema, 'Goju-Ryu Madrid')

    def test_on_demand_tls_check_endpoint(self):
        """Verifica el endpoint /internal/tls-check/ para Caddy On-Demand TLS."""
        self.dojo.dominio_personalizado = "karatesakura.es"
        self.dojo.sitio_activo = True
        self.dojo.save()

        tls_url = reverse('tls_domain_check')
        self.assertEqual(self.client.get(tls_url).status_code, 400)
        self.assertEqual(self.client.get(f"{tls_url}?domain=ogkke.es").status_code, 200)
        self.assertEqual(self.client.get(f"{tls_url}?domain=dojo-test.ogkke.es").status_code, 200)
        self.assertEqual(self.client.get(f"{tls_url}?domain=karatesakura.es").status_code, 200)
        self.assertEqual(self.client.get(f"{tls_url}?domain=desconocido.es").status_code, 403)

        # Si el portal del Dojo se desactiva, no autoriza emisión TLS
        self.dojo.sitio_activo = False
        self.dojo.save()
        self.assertEqual(self.client.get(f"{tls_url}?domain=karatesakura.es").status_code, 403)

    def test_general_activities_appear_in_all_dojos_interleaved_by_date(self):
        """
        Verifica que al crear una actividad general (Actividad), aparece en el tablón
        y portal de todos los dojos intercalada por fecha con las actividades particulares.
        """
        hoy = datetime.date.today()
        Actividad.objects.all().delete()
        Tablon.objects.all().delete()

        # Actividades particulares de self.dojo (día +2 y día +10)
        local_temprana = Tablon.objects.create(
            dojo=self.dojo,
            tipo="Local",
            titulo="Entrenamiento Local Dojo 1",
            descripcion="Sesión especial de kumite",
            fecha=hoy + datetime.timedelta(days=2),
            lugar="Tatami Principal",
        )
        local_tardia = Tablon.objects.create(
            dojo=self.dojo,
            tipo="Examen",
            titulo="Examen Kyu Dojo 1",
            descripcion="Convocatoria trimestral",
            fecha=hoy + datetime.timedelta(days=10),
            lugar="Tatami Principal",
        )

        # Actividad particular de self.other_dojo (día +8)
        local_otro = Tablon.objects.create(
            dojo=self.other_dojo,
            tipo="Local",
            titulo="Clase Especial Dojo 2",
            descripcion="Bunkai avanzado",
            fecha=hoy + datetime.timedelta(days=8),
            lugar="Sala B",
        )

        # Staff crea una actividad general (día +5, entre día +2 y día +8/+10)
        self.client.force_login(self.staff_user)
        fecha_general = hoy + datetime.timedelta(days=5)
        post_res = self.client.post(reverse('administracion:actividades'), {
            'tipo': 'Gasshuku',
            'titulo': 'Actividad General Intercalada',
            'descripcion': 'Convocatoria nacional para todos los dojos',
            'fecha': fecha_general.strftime('%Y-%m-%d'),
            'lugar': 'Pabellón Central',
            'ciudad': 'Madrid',
            'provincia': 'Madrid',
            'pais': 'España',
        })
        self.assertEqual(post_res.status_code, 302)
        actividad_general = Actividad.objects.get(titulo='Actividad General Intercalada')

        # 1. En el Tablón de self.dojo aparece intercalada: [local_temprana (+2), actividad_general (+5), local_tardia (+10)]
        self.client.force_login(self.instructor_user)
        tablon_dojo1 = self.client.get(f"{reverse('administracion:tablon')}?dojo={self.dojo.pk}")
        self.assertEqual(tablon_dojo1.status_code, 200)
        titulos_dojo1 = [item.titulo for item in tablon_dojo1.context['tablon']]
        self.assertEqual(
            titulos_dojo1,
            [local_temprana.titulo, actividad_general.titulo, local_tardia.titulo],
        )
        self.assertContains(tablon_dojo1, 'OGKKE · General')
        # El instructor puede editar sus avisos locales, pero no se genera URL de editar_tablon para la actividad general
        self.assertContains(tablon_dojo1, reverse('administracion:editar_tablon', kwargs={'pk': local_temprana.pk}))

        # 2. En el Portal de self.dojo también aparece intercalada en el mismo orden
        portal_dojo1 = self.client.get(reverse('dojo_portal_public', kwargs={'slug': self.dojo.slug}))
        self.assertEqual(portal_dojo1.status_code, 200)
        self.assertEqual(
            [item.titulo for item in portal_dojo1.context['tablon']],
            [local_temprana.titulo, actividad_general.titulo, local_tardia.titulo],
        )

        # 3. En el Tablón y Portal de self.other_dojo también aparece intercalada: [actividad_general (+5), local_otro (+8)]
        tablon_dojo2 = self.client.get(f"{reverse('administracion:tablon')}?dojo={self.other_dojo.pk}")
        self.assertEqual(tablon_dojo2.status_code, 200)
        self.assertEqual(
            [item.titulo for item in tablon_dojo2.context['tablon']],
            [actividad_general.titulo, local_otro.titulo],
        )
        portal_dojo2 = self.client.get(reverse('dojo_portal_public', kwargs={'slug': self.other_dojo.slug}))
        self.assertEqual(portal_dojo2.status_code, 200)
        self.assertEqual(
            [item.titulo for item in portal_dojo2.context['tablon']],
            [actividad_general.titulo, local_otro.titulo],
        )

    def test_login_routing_confinement_and_dojo_companions_visibility(self):
        """
        Verifica:
        1. Login de alumno (DAN o Color adulto) redirige automáticamente al portal de su Dojo.
        2. El alumno no puede acceder a los listados globales ni al portal de otro Dojo.
        3. En el portal de su Dojo ve su propio historial (exámenes y cursillos) y a sus
           compañeros Cintos Negros con la fecha en que se examinaron.
        4. Puede ver la ficha de un compañero de su mismo Dojo, pero recibe 403 ante un alumno de otro Dojo.
        """
        from administracion.models import AlumnoColor, GradoKyu

        # Compañero Cinto Negro del mismo Dojo con examen registrado
        companero_dan = Alumno.objects.create(
            nombre="Kenji",
            apellidos="Compañero",
            dojo=self.dojo,
            instructor=False,
            grado=2,
            activo=True,
        )
        Examen.objects.create(alumno=companero_dan, evento=self.cursillo, grado=2)

        # Alumno Cinto Negro de OTRO Dojo
        ajeno_dan = Alumno.objects.create(
            nombre="Pedro",
            apellidos="OtroDojo",
            dojo=self.other_dojo,
            instructor=False,
            grado=1,
            activo=True,
        )

        # Examen y asistencia del propio regular_alumno
        self.cursillo.alumnos.add(self.regular_alumno)
        Examen.objects.create(alumno=self.regular_alumno, evento=self.cursillo, grado=1)

        # 1. Login de regular_user redirige al portal de self.dojo
        login_res = self.client.post(reverse('login'), {
            'username': 'regular@test.com',
            'password': 'SecurePassword123!',
        })
        self.assertEqual(login_res.status_code, 302)
        expected_portal_url = reverse('administracion:dojo_portal', kwargs={'slug': self.dojo.slug})
        self.assertEqual(login_res.url, expected_portal_url)

        # 2. Intento de acceder al portal de otro Dojo estando logado -> redirige a su propio Dojo
        other_portal_res = self.client.get(reverse('administracion:dojo_portal', kwargs={'slug': self.other_dojo.slug}))
        self.assertEqual(other_portal_res.status_code, 302)
        self.assertEqual(other_portal_res.url, expected_portal_url)

        # Vistas globales bloqueadas con 403
        self.assertEqual(self.client.get(reverse('administracion:alumnos')).status_code, 403)
        self.assertEqual(self.client.get(reverse('administracion:dojos')).status_code, 403)
        self.assertEqual(self.client.get(reverse('administracion:cursillos')).status_code, 403)

        # 3. En el portal de su Dojo ve los exámenes de sus compañeros y su propio historial
        portal_res = self.client.get(expected_portal_url)
        self.assertEqual(portal_res.status_code, 200)
        self.assertContains(portal_res, 'Compañero, Kenji')
        self.assertContains(portal_res, f"2º DAN ({self.cursillo.fecha.strftime('%d/%m/%Y')})")
        self.assertContains(portal_res, 'Mi Historial Técnico')
        self.assertContains(portal_res, 'Examen 1º DAN')
        self.assertContains(portal_res, self.cursillo.evento)

        # 4. Puede ver la ficha de su compañero de Dojo (200), pero NO la de otro Dojo (403)
        ok_detail = self.client.get(reverse('administracion:alumno_detalle', kwargs={'pk': companero_dan.pk}))
        self.assertEqual(ok_detail.status_code, 200)
        forbidden_detail = self.client.get(reverse('administracion:alumno_detalle', kwargs={'pk': ajeno_dan.pk}))
        self.assertEqual(forbidden_detail.status_code, 403)

    def test_invitacion_adultos_bloqueo_menores_cursillos_color_y_promocion_1_dan(self):
        """
        Verifica:
        1. Prohibición de crear/invitar cuenta de usuario a menores de 18 años.
        2. Invitación por el Instructor a un alumno de Cinturón Marrón mayor de edad (>= 18),
           creando su cuenta y enviando email.
        3. Inscripción de alumno de color en cursillos con abierto_cintos_color=True (y bloqueo si es False).
        4. Promoción de Cinturón Marrón a Cinturón Negro 1º DAN traspasando su cuenta Usuario,
           sus cursillos asistidos y registrando su Examen de 1º DAN.
        """
        from django.core import mail
        from django.core.exceptions import ValidationError
        from administracion.models import AlumnoColor, GradoKyu

        grado_marron = GradoKyu.objects.get(nombre="Marrón")
        hoy = datetime.date.today()

        # 1. Menor de 15 años: no puede tener cuenta de usuario
        menor_15 = AlumnoColor.objects.create(
            nombre="Joven",
            apellidos="Menor",
            fecha_nacimiento=datetime.date(hoy.year - 15, 5, 10),
            dojo=self.dojo,
            grado_actual=grado_marron,
            consentimiento_firmado=True,
            activo=True,
        )
        user_temp = User.objects.create_user(email="menor@test.com", password="Password123!")
        menor_15.usuario = user_temp
        with self.assertRaises(ValidationError):
            menor_15.full_clean()
        menor_15.usuario = None
        user_temp.delete()

        # 2. Adulto de 24 años Cinturón Marrón: el Instructor le invita al Portal
        adulto_marron = AlumnoColor.objects.create(
            nombre="Lucía",
            apellidos="Sánchez Marrón",
            fecha_nacimiento=datetime.date(hoy.year - 24, 3, 15),
            dojo=self.dojo,
            grado_actual=grado_marron,
            activo=True,
        )

        self.client.force_login(self.instructor_user)
        mail.outbox.clear()
        inv_res = self.client.post(
            reverse('administracion:alumno_color_invitar_usuario', kwargs={'codigo': adulto_marron.codigo_interno}),
            {'email': 'lucia.marron@test.com'},
        )
        self.assertEqual(inv_res.status_code, 302)
        adulto_marron.refresh_from_db()
        self.assertIsNotNone(adulto_marron.usuario)
        self.assertEqual(adulto_marron.usuario.email, 'lucia.marron@test.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.dojo.nombre, mail.outbox[0].subject)

        # 3. Lucía inicia sesión y se inscribe a un cursillo abierto a cintos de color
        usuario_lucia = adulto_marron.usuario
        usuario_lucia.set_password("LuciaSecure123!")
        usuario_lucia.save()

        self.client.force_login(usuario_lucia)
        # Intentar inscribirse en cursillo exclusivo de cintos negros -> rechazado
        self.cursillo.abierto_cintos_color = False
        self.cursillo.save()
        insc_url = reverse('administracion:cursillo_inscripcion_alumno', kwargs={'pk': self.cursillo.pk})
        self.client.post(insc_url, {'action': 'inscribir'})
        self.assertFalse(self.cursillo.alumnos_color.filter(pk=adulto_marron.pk).exists())

        # Habilitar abierto_cintos_color=True -> inscripción directa exitosa
        self.cursillo.abierto_cintos_color = True
        self.cursillo.examenes = True
        self.cursillo.save()
        res_insc_ok = self.client.post(insc_url, {
            'action': 'inscribir',
            'next': reverse('administracion:dojo_portal', kwargs={'slug': self.dojo.slug}),
        })
        self.assertEqual(res_insc_ok.status_code, 302)
        self.assertTrue(self.cursillo.alumnos_color.filter(pk=adulto_marron.pk).exists())

        # 4. El Instructor promociona a Lucía de Cinturón Marrón a Cinturón Negro 1º DAN
        self.client.force_login(self.instructor_user)
        promo_res = self.client.post(
            reverse('administracion:alumno_color_promocionar_dan', kwargs={'codigo': adulto_marron.codigo_interno}),
            {'cursillo_examen': self.cursillo.pk},
        )
        self.assertEqual(promo_res.status_code, 302)

        nuevo_dan = Alumno.objects.get(alumno_color_origen=adulto_marron)
        self.assertEqual(nuevo_dan.grado, 1)
        self.assertEqual(nuevo_dan.usuario, usuario_lucia)
        self.assertTrue(self.cursillo.alumnos.filter(pk=nuevo_dan.pk).exists())
        self.assertTrue(Examen.objects.filter(alumno=nuevo_dan, evento=self.cursillo, grado=1).exists())







