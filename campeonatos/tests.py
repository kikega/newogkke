"""
Tests unitarios y de integración para:
1. Gestión de Cinturones de Color (Kyu) y Protección de Menores (RGPD / LOPDGDD).
2. Aislamiento estricto por Dojo (Anti-IDOR entre instructores).
3. Cálculo de edad por fecha exacta de cumpleaños el día del campeonato.
4. Prohibición de Kumite para menores de 18 años.
5. Jueces efímeros de Tatami y bloqueo de login una vez finalizado el torneo.
6. Avance de rondas por Puntuación (Top N + creación de nueva ronda en desempate),
   Banderas (Aka vs Ao) y consolidación de ResultadoHistorico inmutable.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from administracion.models import Alumno, AlumnoColor, Dojo, GradoKyu, HistorialGradoKyu
from campeonatos.models import (
    ActuacionPuntuacion,
    Campeonato,
    CategoriaCampeonato,
    InscripcionCampeonato,
    ResultadoHistorico,
    Tatami,
)
from campeonatos.services import (
    cerrar_y_avanzar_ronda_banderas,
    cerrar_y_avanzar_ronda_puntuacion,
    crear_credenciales_juez_tatami,
    iniciar_competicion_categoria,
)

User = get_user_model()


class CinturonesColorYCampeonatosTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.hoy = datetime.date.today()

        self.instructor_group, _ = Group.objects.get_or_create(name='Instructor')

        # Dojos A y B para pruebas de aislamiento cruzado
        self.dojo_a = Dojo.objects.create(
            nombre="Dojo Goju Madrid",
            direccion="Calle Alcalá 10",
            poblacion="Madrid",
            provincia="Madrid",
            codigo_postal="28001",
        )
        self.dojo_b = Dojo.objects.create(
            nombre="Dojo Goju Alicante",
            direccion="Avenida Mar 20",
            poblacion="Alicante",
            provincia="Alicante",
            codigo_postal="03001",
        )

        # Staff de la asociación
        self.staff_user = User.objects.create_user(
            email="staff_nacional@ogkke.es",
            password="SecurePassword123!",
            is_staff=True,
        )

        # Instructor Dojo A
        self.inst_a_user = User.objects.create_user(
            email="sensei_madrid@ogkke.es",
            password="SecurePassword123!",
        )
        self.inst_a_user.groups.add(self.instructor_group)
        self.inst_a = Alumno.objects.create(
            usuario=self.inst_a_user,
            nombre="Takeshi",
            apellidos="Madrid",
            dojo=self.dojo_a,
            instructor=True,
            grado=5,
            activo=True,
        )

        # Instructor Dojo B
        self.inst_b_user = User.objects.create_user(
            email="sensei_alicante@ogkke.es",
            password="SecurePassword123!",
        )
        self.inst_b_user.groups.add(self.instructor_group)
        self.inst_b = Alumno.objects.create(
            usuario=self.inst_b_user,
            nombre="Hiroshi",
            apellidos="Alicante",
            dojo=self.dojo_b,
            instructor=True,
            grado=4,
            activo=True,
        )

        # Alumno Cinturón Negro regular (no instructor)
        self.regular_user = User.objects.create_user(
            email="cintonegro@ogkke.es",
            password="SecurePassword123!",
        )
        self.regular_alumno = Alumno.objects.create(
            usuario=self.regular_user,
            nombre="Carlos",
            apellidos="Practicante",
            fecha_nacimiento=datetime.date(1995, 5, 10),
            dojo=self.dojo_a,
            instructor=False,
            grado=1,
            activo=True,
        )

        # Obtener grados Kyu sembrados por la migración 0019
        self.grado_blanco = GradoKyu.objects.get(nombre="Blanco")
        self.grado_blanco_amarillo = GradoKyu.objects.get(nombre="Blanco-Amarillo")
        self.grado_amarillo = GradoKyu.objects.get(nombre="Amarillo")
        self.grado_naranja = GradoKyu.objects.get(nombre="Naranja")
        self.grado_verde = GradoKyu.objects.get(nombre="Verde")
        self.grado_marron = GradoKyu.objects.get(nombre="Marrón")

        # Crear un menor de 9 años con autorización paterna válida en el Dojo A
        fecha_nac_9 = datetime.date(self.hoy.year - 9, self.hoy.month, min(self.hoy.day, 28))
        self.menor_dojo_a = AlumnoColor.objects.create(
            nombre="Lucas",
            apellidos="García Menor",
            fecha_nacimiento=fecha_nac_9,
            genero="M",
            dojo=self.dojo_a,
            grado_actual=self.grado_amarillo,
            consentimiento_firmado=True,
            consentimiento_campeonatos=True,
            fecha_firma_consentimiento=self.hoy,
            referencia_consentimiento="RGPD-MAD-001",
            activo=True,
        )

        # Crear un menor de 9 años en el Dojo B
        self.menor_dojo_b = AlumnoColor.objects.create(
            nombre="Sofía",
            apellidos="Martínez Menor",
            fecha_nacimiento=fecha_nac_9,
            genero="F",
            dojo=self.dojo_b,
            grado_actual=self.grado_naranja,
            consentimiento_firmado=True,
            consentimiento_campeonatos=True,
            fecha_firma_consentimiento=self.hoy,
            referencia_consentimiento="RGPD-ALI-001",
            activo=True,
        )

    def test_catalogo_grados_kyu_jerarquia_completa(self):
        """Verifica que existen los 11 grados de cinturón de color ordenados jerárquicamente."""
        grados = list(GradoKyu.objects.values_list('nombre', flat=True))
        esperados = [
            'Blanco',
            'Blanco-Amarillo',
            'Amarillo',
            'Amarillo-Naranja',
            'Naranja',
            'Naranja-Verde',
            'Verde',
            'Verde-Azul',
            'Azul',
            'Azul-Marrón',
            'Marrón',
        ]
        self.assertEqual(grados, esperados)
        self.assertTrue(self.grado_blanco_amarillo.es_intermedio_infantil)
        self.assertFalse(self.grado_marron.es_intermedio_infantil)

    def test_aislamiento_estricto_entre_dojos_anti_idor(self):
        """
        Verifica que un instructor del Dojo B NO puede ver, acceder por URL (IDOR),
        editar, ascender ni eliminar bajo ningún concepto a un menor del Dojo A.
        """
        # 1. Nivel QuerySet Manager (for_user)
        qs_inst_a = AlumnoColor.objects.for_user(self.inst_a_user)
        qs_inst_b = AlumnoColor.objects.for_user(self.inst_b_user)
        qs_regular = AlumnoColor.objects.for_user(self.regular_user)
        qs_staff = AlumnoColor.objects.for_user(self.staff_user)

        self.assertEqual(list(qs_inst_a), [self.menor_dojo_a])
        self.assertEqual(list(qs_inst_b), [self.menor_dojo_b])
        self.assertEqual(qs_regular.count(), 0)
        self.assertEqual(qs_staff.count(), 2)

        # 2. Instructor B intentando acceder a la ficha o acciones del menor del Dojo A
        self.client.force_login(self.inst_b_user)

        list_res = self.client.get(reverse('administracion:alumnos_color'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, self.menor_dojo_b.apellidos)
        self.assertNotContains(list_res, self.menor_dojo_a.apellidos)

        # Intento de acceso directo por UUID a la ficha del menor del Dojo A -> 403
        detail_res = self.client.get(
            reverse('administracion:alumno_color_detalle', kwargs={'codigo': self.menor_dojo_a.codigo_interno})
        )
        self.assertEqual(detail_res.status_code, 403)

        # Intento de edición cruzada -> 403
        edit_res = self.client.post(
            reverse('administracion:alumno_color_editar', kwargs={'codigo': self.menor_dojo_a.codigo_interno}),
            {'nombre': 'Hacked'},
        )
        self.assertEqual(edit_res.status_code, 403)

        # Intento de ascenso cruzado -> 403
        asc_res = self.client.post(
            reverse('administracion:alumno_color_ascenso', kwargs={'codigo': self.menor_dojo_a.codigo_interno}),
            {'nuevo_grado': self.grado_verde.id, 'fecha_examen': str(self.hoy)},
        )
        self.assertEqual(asc_res.status_code, 403)

        # Intento de eliminación cruzada -> 403
        del_res = self.client.post(
            reverse('administracion:alumno_color_eliminar', kwargs={'codigo': self.menor_dojo_a.codigo_interno})
        )
        self.assertEqual(del_res.status_code, 403)
        self.assertTrue(AlumnoColor.objects.filter(pk=self.menor_dojo_a.pk).exists())

        # 3. Alumno cinturón negro regular no tiene acceso al módulo de cintos de color -> 403
        self.client.force_login(self.regular_user)
        self.assertEqual(self.client.get(reverse('administracion:alumnos_color')).status_code, 403)

        # 4. El portal público del Dojo NUNCA muestra a los menores de cinturón de color
        self.client.logout()
        portal_res = self.client.get(reverse('dojo_portal_public', kwargs={'slug': self.dojo_a.slug}))
        self.assertEqual(portal_res.status_code, 200)
        self.assertNotContains(portal_res, self.menor_dojo_a.apellidos)

    def test_proteccion_menores_14_anios_lopdgdd_alta_e_inscripcion(self):
        """
        Verifica que un menor de 14 años no puede darse de alta activa ni inscribirse
        en un campeonato si no tiene el consentimiento paterno firmado y fechado.
        """
        fecha_nac_10 = datetime.date(self.hoy.year - 10, 6, 15)
        menor_sin_firma = AlumnoColor(
            nombre="Pablo",
            apellidos="Sin Consentimiento",
            fecha_nacimiento=fecha_nac_10,
            dojo=self.dojo_a,
            grado_actual=self.grado_blanco,
            consentimiento_firmado=False,
            activo=True,
        )
        with self.assertRaises(ValidationError):
            menor_sin_firma.full_clean()

        # Puede guardarse como inactivo mientras trae el papel firmado, pero no competir
        menor_sin_firma.activo = False
        menor_sin_firma.save()
        self.assertFalse(menor_sin_firma.puede_competir)

    def test_calculo_edad_exacta_por_cumpleanios_en_fecha_del_torneo(self):
        """
        Verifica la regla de edad por fecha exacta de cumpleaños:
        Si el competidor nació el 25 de noviembre de 2019:
        - En el Torneo de Otoño (20 de noviembre de 2026) tiene 6 años.
        - En el Torneo de Invierno (1 de diciembre de 2026) ya ha cumplido 7 años.
        """
        nino = AlumnoColor.objects.create(
            nombre="Mateo",
            apellidos="Cumpleaños Noviembre",
            fecha_nacimiento=datetime.date(2019, 11, 25),
            dojo=self.dojo_a,
            grado_actual=self.grado_blanco_amarillo,
            consentimiento_firmado=True,
            consentimiento_campeonatos=True,
            fecha_firma_consentimiento=self.hoy,
            activo=True,
        )

        torneo_antes_cumple = Campeonato.objects.create(
            nombre="Copa Otoño",
            ambito="GENERAL",
            fecha_inicio=datetime.date(2026, 11, 20),
            fecha_fin=datetime.date(2026, 11, 21),
            lugar="Polideportivo",
            ciudad="Madrid",
            estado="INSCRIPCION",
        )
        torneo_despues_cumple = Campeonato.objects.create(
            nombre="Copa Invierno",
            ambito="GENERAL",
            fecha_inicio=datetime.date(2026, 12, 1),
            fecha_fin=datetime.date(2026, 12, 2),
            lugar="Polideportivo",
            ciudad="Madrid",
            estado="INSCRIPCION",
        )

        self.assertEqual(torneo_antes_cumple.calcular_edad_competidor(nino.fecha_nacimiento), 6)
        self.assertEqual(torneo_despues_cumple.calcular_edad_competidor(nino.fecha_nacimiento), 7)

        cat_7_anios_otono = CategoriaCampeonato.objects.create(
            campeonato=torneo_antes_cumple,
            nombre="Alevín 7 años",
            modalidad="KATA",
            sistema="PUNTOS",
            edad_min=7,
            edad_max=7,
        )
        # En el torneo del 20 de noviembre aún tiene 6 años -> debe rechazarse en categoría de 7 años
        insc_invalida = InscripcionCampeonato(categoria=cat_7_anios_otono, alumno_color=nino)
        with self.assertRaises(ValidationError):
            insc_invalida.full_clean()

        # En cambio, en el torneo del 1 de diciembre ya tiene 7 años -> inscripción válida
        cat_7_anios_invierno = CategoriaCampeonato.objects.create(
            campeonato=torneo_despues_cumple,
            nombre="Alevín 7 años Invierno",
            modalidad="KATA",
            sistema="PUNTOS",
            edad_min=7,
            edad_max=7,
        )
        insc_valida = InscripcionCampeonato.objects.create(categoria=cat_7_anios_invierno, alumno_color=nino)
        self.assertEqual(insc_valida.edad_en_torneo, 7)

    def test_kumite_restringido_exclusivamente_a_mayores_de_edad(self):
        """
        Verifica que Kumite solo permite categorías con edad_min >= 18 y bloquea
        cualquier intento de inscribir a menores de 18 años.
        """
        torneo = Campeonato.objects.create(
            nombre="Nacional OGKKE",
            ambito="GENERAL",
            fecha_inicio=self.hoy,
            fecha_fin=self.hoy + datetime.timedelta(days=1),
            lugar="Pabellón Central",
            ciudad="Madrid",
            estado="INSCRIPCION",
        )

        # Intentar crear categoría de Kumite para menores de 18 -> ValidationError
        cat_kumite_menor = CategoriaCampeonato(
            campeonato=torneo,
            nombre="Kumite Juvenil",
            modalidad="KUMITE",
            edad_min=16,
            edad_max=17,
        )
        with self.assertRaises(ValidationError):
            cat_kumite_menor.full_clean()

        # Categoría Kumite Senior (+18) válida
        cat_kumite_senior = CategoriaCampeonato.objects.create(
            campeonato=torneo,
            nombre="Kumite Senior Absoluto (+18)",
            modalidad="KUMITE",
            edad_min=18,
            edad_max=60,
            admite_cintos_color=True,
            admite_cintos_negros=True,
        )
        self.assertEqual(cat_kumite_senior.sistema, "BANDERAS")

        # Intentar inscribir al menor de 9 años en Kumite -> ValidationError
        with self.assertRaises(ValidationError):
            InscripcionCampeonato.objects.create(
                categoria=cat_kumite_senior,
                alumno_color=self.menor_dojo_a,
            )

        # Inscribir al adulto de Cinturón Negro (>18 años) -> OK
        insc_adulto = InscripcionCampeonato.objects.create(
            categoria=cat_kumite_senior,
            alumno_dan=self.regular_alumno,
        )
        self.assertGreaterEqual(insc_adulto.edad_en_torneo, 18)

    def test_juez_efimero_tatami_acceso_en_fecha_y_bloqueo_login_tras_torneo(self):
        """
        Verifica que el usuario temporal del Tatami:
        1. Puede iniciar sesión y operar su Tatami durante las fechas del torneo.
        2. NO puede acceder a otros tatamis ni al listado de cinturones de color.
        3. Una vez pasadas las fechas del torneo (o finalizado), NO puede logarse en el sistema.
        """
        torneo = Campeonato.objects.create(
            nombre="Copa Primavera",
            ambito="GENERAL",
            fecha_inicio=self.hoy,
            fecha_fin=self.hoy + datetime.timedelta(days=1),
            lugar="Pabellón",
            ciudad="Madrid",
            estado="EN_CURSO",
        )
        tatami1 = Tatami.objects.create(campeonato=torneo, numero=1, nombre="Tatami 1")
        tatami2 = Tatami.objects.create(campeonato=torneo, numero=2, nombre="Tatami 2")

        juez_user, email_juez, password_juez = crear_credenciales_juez_tatami(tatami1)

        # 1. Login exitoso durante las fechas del torneo -> redirige directo a Tatami 1
        login_res = self.client.post(reverse('login'), {
            'username': email_juez,
            'password': password_juez,
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertIn(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami1.id}), login_res.url)

        # Puede ver su Tatami 1
        t1_res = self.client.get(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami1.id}))
        self.assertEqual(t1_res.status_code, 200)

        # NO puede ver el Tatami 2 -> 403
        t2_res = self.client.get(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami2.id}))
        self.assertEqual(t2_res.status_code, 403)

        # NO puede acceder al censo de cinturones de color ni a dojos -> 403
        self.assertEqual(self.client.get(reverse('administracion:alumnos_color')).status_code, 403)
        self.assertEqual(self.client.get(reverse('administracion:dojos')).status_code, 403)

        # 2. Cuando pasa la fecha del torneo, su sesión se cierra y ya NO puede volver a logarse
        torneo.fecha_inicio = self.hoy - datetime.timedelta(days=5)
        torneo.fecha_fin = self.hoy - datetime.timedelta(days=4)
        torneo.save()

        # Cualquier petición posterior lo desloguea y redirige a login
        expired_res = self.client.get(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami1.id}))
        self.assertEqual(expired_res.status_code, 302)
        self.assertIn(reverse('login'), expired_res.url)

        # Intentar logarse una vez pasado el torneo -> Bloqueado (200 con mensaje de error, sin sesión)
        relogin_res = self.client.post(reverse('login'), {
            'username': email_juez,
            'password': password_juez,
        })
        self.assertEqual(relogin_res.status_code, 200)
        self.assertContains(
            relogin_res,
            "El acceso de Juez de Tatami solo está habilitado durante las fechas oficiales del campeonato.",
        )
        self.assertFalse(relogin_res.wsgi_request.user.is_authenticated)

    def test_flujo_completo_puntuacion_corte_top_n_desempate_e_historico(self):
        """
        Verifica el flujo completo en sistema de puntuación:
        - 3 competidores compiten por 2 plazas para la Final (clasificados_siguiente_ronda=2).
        - El 2º y 3º empatan en puntuación en la Ronda Clasificatoria -> se crea una
          nueva Ronda de Desempate de Clasificación solo con los 2 empatados.
        - Tras puntuar el desempate, se crea la Ronda Final con los 2 clasificados.
        - Tras puntuar la Final, se cierra la categoría y se guarda el ResultadoHistorico inmutable.
        """
        torneo = Campeonato.objects.create(
            nombre="Torneo Interdojos",
            ambito="GENERAL",
            fecha_inicio=self.hoy,
            fecha_fin=self.hoy,
            lugar="Central",
            ciudad="Madrid",
            estado="EN_CURSO",
        )
        tatami = Tatami.objects.create(campeonato=torneo, numero=1, nombre="Tatami Central", num_jueces_mesa=3)
        categoria = CategoriaCampeonato.objects.create(
            campeonato=torneo,
            tatami=tatami,
            nombre="Alevín Mixto Kata (8-10 años)",
            modalidad="KATA",
            sistema="PUNTOS",
            edad_min=8,
            edad_max=10,
            clasificados_siguiente_ronda=2,
        )

        fecha_nac_9 = datetime.date(self.hoy.year - 9, 1, 10)
        c3 = AlumnoColor.objects.create(
            nombre="Elena",
            apellidos="Tercera",
            fecha_nacimiento=fecha_nac_9,
            dojo=self.dojo_a,
            grado_actual=self.grado_amarillo,
            consentimiento_firmado=True,
            consentimiento_campeonatos=True,
            fecha_firma_consentimiento=self.hoy,
            activo=True,
        )

        i1 = InscripcionCampeonato.objects.create(categoria=categoria, alumno_color=self.menor_dojo_a)
        i2 = InscripcionCampeonato.objects.create(categoria=categoria, alumno_color=self.menor_dojo_b)
        i3 = InscripcionCampeonato.objects.create(categoria=categoria, alumno_color=c3)

        # Iniciar Ronda 1
        ronda1 = iniciar_competicion_categoria(categoria)
        self.assertEqual(ronda1.numero, 1)
        self.assertFalse(ronda1.es_final)

        act1 = ActuacionPuntuacion.objects.get(ronda=ronda1, inscripcion=i1)
        act2 = ActuacionPuntuacion.objects.get(ronda=ronda1, inscripcion=i2)
        act3 = ActuacionPuntuacion.objects.get(ronda=ronda1, inscripcion=i3)

        # i1 obtiene 24.0 (pasa directo), i2 e i3 empatan a 21.0 por la 2ª plaza
        act1.registrar_notas([Decimal('8.0'), Decimal('8.0'), Decimal('8.0')])
        act2.registrar_notas([Decimal('7.0'), Decimal('7.0'), Decimal('7.0')])
        act3.registrar_notas([Decimal('7.0'), Decimal('7.0'), Decimal('7.0')])

        res_cierre1 = cerrar_y_avanzar_ronda_puntuacion(ronda1)
        self.assertEqual(res_cierre1['estado'], 'DESEMPATE_CORTE')
        ronda_desempate = res_cierre1['ronda_creada']
        self.assertTrue(ronda_desempate.es_desempate)
        self.assertEqual(ronda_desempate.actuaciones.count(), 2)

        # Puntuar la ronda de desempate entre i2 e i3
        act_des_2 = ActuacionPuntuacion.objects.get(ronda=ronda_desempate, inscripcion=i2)
        act_des_3 = ActuacionPuntuacion.objects.get(ronda=ronda_desempate, inscripcion=i3)
        act_des_2.registrar_notas([Decimal('7.5'), Decimal('7.5'), Decimal('7.5')])
        act_des_3.registrar_notas([Decimal('7.1'), Decimal('7.1'), Decimal('7.1')])

        res_cierre_des = cerrar_y_avanzar_ronda_puntuacion(ronda_desempate)
        self.assertEqual(res_cierre_des['estado'], 'RONDA_FINAL_CREADA')
        ronda_final = res_cierre_des['ronda_creada']
        self.assertTrue(ronda_final.es_final)
        self.assertEqual(ronda_final.actuaciones.count(), 2)

        # Puntuar la Final
        final_i1 = ActuacionPuntuacion.objects.get(ronda=ronda_final, inscripcion=i1)
        final_i2 = ActuacionPuntuacion.objects.get(ronda=ronda_final, inscripcion=i2)
        final_i1.registrar_notas([Decimal('8.5'), Decimal('8.5'), Decimal('8.5')])
        final_i2.registrar_notas([Decimal('8.0'), Decimal('8.0'), Decimal('8.0')])

        res_final = cerrar_y_avanzar_ronda_puntuacion(ronda_final)
        self.assertEqual(res_final['estado'], 'FINALIZADA')

        categoria.refresh_from_db()
        self.assertEqual(categoria.estado, 'FINALIZADA')

        historico = list(ResultadoHistorico.objects.filter(categoria=categoria).order_by('puesto'))
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0].puesto, 1)
        self.assertEqual(historico[0].nombre_competidor_snapshot, i1.nombre_competidor)
        self.assertEqual(historico[0].grado_snapshot, "Amarillo")

        # Aunque el alumno ascienda después a cinturón Verde, el snapshot histórico permanece inmutable
        self.menor_dojo_a.grado_actual = self.grado_verde
        self.menor_dojo_a.save()
        historico[0].refresh_from_db()
        self.assertEqual(historico[0].grado_snapshot, "Amarillo")

    def test_sistema_ayuda_campeonatos_para_jueces_e_instructores(self):
        """
        Verifica que el Centro de Ayuda (/campeonatos/ayuda/) y el diálogo contextual
        de ayuda están disponibles tanto para Instructores y Staff como para Jueces
        Efímeros de Tatami durante las fechas del torneo.
        """
        torneo = Campeonato.objects.create(
            nombre="Copa Ayuda",
            ambito="GENERAL",
            fecha_inicio=self.hoy,
            fecha_fin=self.hoy + datetime.timedelta(days=1),
            lugar="Central",
            ciudad="Madrid",
            estado="EN_CURSO",
        )
        tatami = Tatami.objects.create(campeonato=torneo, numero=1, nombre="Tatami 1")
        juez_user, _, _ = crear_credenciales_juez_tatami(tatami)

        # 1. Instructor consulta el Centro de Ayuda
        self.client.force_login(self.inst_a_user)
        res_inst = self.client.get(reverse('campeonatos:ayuda'))
        self.assertEqual(res_inst.status_code, 200)
        self.assertEqual(res_inst.context['rol_activo'], 'instructor')
        self.assertContains(res_inst, 'Centro de Ayuda · Módulo de Campeonatos')
        self.assertContains(res_inst, 'name="faq-juez"')
        self.assertContains(res_inst, 'name="faq-instructor"')

        # 2. Juez efímero de Tatami puede consultar la ayuda contextual en su Tatami y el Centro de Ayuda
        self.client.force_login(juez_user)
        res_tatami = self.client.get(reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id}))
        self.assertEqual(res_tatami.status_code, 200)
        self.assertContains(res_tatami, 'id="modalAyudaCampeonatos"')
        self.assertContains(res_tatami, 'commandfor="modalAyudaCampeonatos"')

        res_juez_ayuda = self.client.get(reverse('campeonatos:ayuda'))
        self.assertEqual(res_juez_ayuda.status_code, 200)
        self.assertEqual(res_juez_ayuda.context['rol_activo'], 'juez')
        self.assertContains(res_juez_ayuda, 'Volver a mi Tatami en Vivo')

