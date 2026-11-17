"""
Vistas Basadas en Clases (CBV) para la gestión de Campeonatos, Categorías,
Inscripciones, Panel Operativo de Tatami en Tiempo Real e Histórico de Resultados.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from administracion.models import AlumnoColor
from administracion.permissions import (
    InstructorOrStaffRequiredMixin,
    es_usuario_juez_efimero,
    obtener_dojo_instructor,
    obtener_tatamis_activos_juez,
    usuario_es_staff_asociacion,
)
from campeonatos.forms import (
    CampeonatoForm,
    CategoriaCampeonatoForm,
    InscripcionCompetidorForm,
    TatamiForm,
)
from campeonatos.models import (
    ActuacionPuntuacion,
    Campeonato,
    CategoriaCampeonato,
    EnfrentamientoBanderas,
    InscripcionCampeonato,
    ResultadoHistorico,
    RondaCategoria,
    Tatami,
)
from campeonatos.services import (
    cerrar_y_avanzar_ronda_banderas,
    cerrar_y_avanzar_ronda_puntuacion,
    crear_credenciales_juez_tatami,
    iniciar_competicion_categoria,
)


def usuario_puede_administrar_campeonato(user, campeonato):
    """
    Determina si el usuario puede configurar tatamis/categorías del campeonato:
    - Staff o Superuser: cualquier campeonato.
    - Instructor titular: campeonatos de ámbito LOCAL de su propio Dojo.
    """
    if usuario_es_staff_asociacion(user):
        return True
    dojo_inst = obtener_dojo_instructor(user)
    return bool(
        dojo_inst
        and campeonato.ambito == 'LOCAL'
        and campeonato.dojo_organizador_id == dojo_inst.id
    )


def usuario_puede_inscribir_en_campeonato(user, campeonato):
    """
    Determina si un usuario puede inscribir alumnos en un campeonato:
    - Staff: siempre.
    - Instructor: en campeonatos GENERALES (inscribe a los alumnos de su Dojo)
      o en campeonatos LOCALES de su propio Dojo.
    """
    if usuario_es_staff_asociacion(user):
        return True
    dojo_inst = obtener_dojo_instructor(user)
    if not dojo_inst:
        return False
    if campeonato.ambito == 'GENERAL':
        return True
    return campeonato.dojo_organizador_id == dojo_inst.id


def verificar_permiso_operacion_tatami(user, tatami):
    """
    Verifica que el usuario autenticado tenga permiso para operar un Tatami en vivo:
    1. Staff o Superusuario de OGKKE.
    2. Instructor organizador si el campeonato es LOCAL de su Dojo.
    3. El Juez Operador asignado a ESE tatami específico, SIEMPRE Y CUANDO
       el campeonato se encuentre dentro de sus fechas activas [fecha_inicio, fecha_fin]
       y no haya finalizado.
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("Debe iniciar sesión.")
    if usuario_puede_administrar_campeonato(user, tatami.campeonato):
        return True
    if tatami.juez_operador_id == user.id:
        if not tatami.acceso_operador_vigente():
            raise PermissionDenied(
                "Acceso denegado: el campeonato no se encuentra dentro de sus fechas activas o ya ha finalizado."
            )
        return True
    raise PermissionDenied("No tiene autorización para operar este Tatami.")


class CampeonatosListView(LoginRequiredMixin, ListView):
    """Listado de campeonatos visibles según el rol del usuario."""
    model = Campeonato
    template_name = 'campeonatos/lista.html'
    context_object_name = 'campeonatos'

    def get_queryset(self):
        return (
            Campeonato.objects.visibles_para(self.request.user)
            .select_related('dojo_organizador')
            .prefetch_related('tatamis', 'categorias')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        puede_crear = usuario_es_staff_asociacion(user) or (obtener_dojo_instructor(user) is not None)
        context['puede_crear_campeonato'] = puede_crear
        context['form_campeonato'] = CampeonatoForm(user=user) if puede_crear else None
        context['ultimos_resultados'] = (
            ResultadoHistorico.objects.select_related('campeonato', 'categoria')
            .filter(puesto__lte=3)
            .order_by('-fecha_registro', 'puesto')[:12]
        )
        return context


class CampeonatoCreateView(InstructorOrStaffRequiredMixin, View):
    """Crea un nuevo Campeonato (General por Staff, o Local por Instructor/Staff)."""

    def post(self, request):
        user = request.user
        es_staff = usuario_es_staff_asociacion(user)
        dojo_inst = obtener_dojo_instructor(user)

        post_data = request.POST.copy()
        if not es_staff:
            if not dojo_inst:
                raise PermissionDenied("No tiene Dojo asignado para organizar un campeonato local.")
            post_data['ambito'] = 'LOCAL'
            post_data['dojo_organizador'] = str(dojo_inst.pk)

        form = CampeonatoForm(post_data, user=user)
        if form.is_valid():
            campeonato = form.save(commit=False)
            campeonato.creado_por = user
            campeonato.save()
            messages.success(request, f"Campeonato '{campeonato.nombre}' creado correctamente.")
            return redirect('campeonatos:detalle', slug=campeonato.slug)

        errores = "; ".join(f"{c}: {', '.join(e)}" for c, e in form.errors.items())
        messages.error(request, f"Error al crear el campeonato: {errores}")
        return redirect('campeonatos:lista')


class CampeonatoDetailView(LoginRequiredMixin, DetailView):
    """Panel central de un Campeonato: Tatamis, Categorías, Inscripciones y Podios."""
    model = Campeonato
    template_name = 'campeonatos/detalle.html'
    context_object_name = 'campeonato'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        camp = get_object_or_404(
            Campeonato.objects.select_related('dojo_organizador'),
            slug=self.kwargs['slug'],
        )
        if not Campeonato.objects.visibles_para(self.request.user).filter(pk=camp.pk).exists():
            raise PermissionDenied("No tiene autorización para ver este campeonato.")
        return camp

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        camp = self.object
        user = self.request.user
        puede_admin = usuario_puede_administrar_campeonato(user, camp)
        puede_inscribir = usuario_puede_inscribir_en_campeonato(user, camp)

        tatamis = camp.tatamis.select_related('juez_operador').prefetch_related('categorias').all()
        categorias = camp.categorias.select_related('tatami', 'grado_kyu_min', 'grado_kyu_max').prefetch_related('inscripciones').all()
        resultados = camp.resultados_historicos.select_related('categoria').order_by('categoria__orden_ejecucion', 'puesto')

        siguiente_num_tatami = (tatamis.count() + 1)
        context.update({
            'puede_administrar': puede_admin,
            'puede_inscribir': puede_inscribir,
            'tatamis': tatamis,
            'categorias': categorias,
            'resultados_historicos': resultados,
            'form_tatami': TatamiForm(initial={'numero': siguiente_num_tatami, 'nombre': f"Tatami {siguiente_num_tatami}"}) if puede_admin else None,
            'form_categoria': CategoriaCampeonatoForm(campeonato=camp, initial={'sistema': camp.sistema_puntuacion_default}) if puede_admin else None,
        })
        return context


class TatamiCreateView(InstructorOrStaffRequiredMixin, View):
    """Añade un Tatami al campeonato y genera opcionalmente el usuario efímero de juez."""

    def post(self, request, slug):
        camp = get_object_or_404(Campeonato, slug=slug)
        if not usuario_puede_administrar_campeonato(request.user, camp):
            raise PermissionDenied("No tiene permiso para configurar tatamis en este campeonato.")

        form = TatamiForm(request.POST)
        if form.is_valid():
            tatami = form.save(commit=False)
            tatami.campeonato = camp
            try:
                tatami.full_clean()
                tatami.save()
                if form.cleaned_data.get('generar_credenciales'):
                    _, email_juez, password_plano = crear_credenciales_juez_tatami(tatami)
                    messages.success(
                        request,
                        f"Tatami {tatami.numero} creado. Credenciales efímeras generadas — "
                        f"Usuario: {email_juez} | Contraseña: {password_plano} "
                        f"(válidas únicamente del {camp.fecha_inicio} al {camp.fecha_fin}).",
                    )
                else:
                    messages.success(request, f"Tatami {tatami.numero} añadido correctamente.")
            except ValidationError as exc:
                messages.error(request, f"No se pudo crear el tatami: {'; '.join(exc.messages)}")
        else:
            messages.error(request, "Datos de tatami no válidos.")
        return redirect('campeonatos:detalle', slug=camp.slug)


class TatamiRegenerarCredencialesView(InstructorOrStaffRequiredMixin, View):
    """Regenera la contraseña temporal del usuario juez operador de un Tatami."""

    def post(self, request, tatami_id):
        tatami = get_object_or_404(Tatami.objects.select_related('campeonato'), pk=tatami_id)
        if not usuario_puede_administrar_campeonato(request.user, tatami.campeonato):
            raise PermissionDenied("No tiene permiso para gestionar credenciales de este Tatami.")

        _, email_juez, password_plano = crear_credenciales_juez_tatami(tatami)
        messages.success(
            request,
            f"Credenciales regeneradas para {tatami.nombre} — Usuario: {email_juez} | Contraseña temporal: {password_plano}",
        )
        return redirect('campeonatos:detalle', slug=tatami.campeonato.slug)


class CategoriaCreateView(InstructorOrStaffRequiredMixin, View):
    """Crea una Categoría de Campeonato validando reglas de modalidad (Kumite >= 18 años)."""

    def post(self, request, slug):
        camp = get_object_or_404(Campeonato, slug=slug)
        if not usuario_puede_administrar_campeonato(request.user, camp):
            raise PermissionDenied("No tiene permiso para crear categorías en este campeonato.")

        form = CategoriaCampeonatoForm(request.POST, campeonato=camp)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.campeonato = camp
            try:
                categoria.save()
                messages.success(request, f"Categoría '{categoria.nombre}' creada correctamente.")
            except ValidationError as exc:
                messages.error(request, f"Error de validación: {'; '.join(exc.messages)}")
        else:
            errores = "; ".join(f"{c}: {', '.join(e)}" for c, e in form.errors.items())
            messages.error(request, f"No se pudo crear la categoría: {errores}")
        return redirect('campeonatos:detalle', slug=camp.slug)


class CategoriaDetailView(InstructorOrStaffRequiredMixin, DetailView):
    """
    Vista de gestión de una Categoría: listado de inscritos, formulario de inscripción
    filtrado por Dojo y botón de inicio de rondas.
    """
    model = CategoriaCampeonato
    template_name = 'campeonatos/categoria_detalle.html'
    context_object_name = 'categoria'

    def get_object(self, queryset=None):
        cat = get_object_or_404(
            CategoriaCampeonato.objects.select_related('campeonato', 'tatami', 'grado_kyu_min', 'grado_kyu_max'),
            pk=self.kwargs['pk'],
        )
        if not usuario_puede_inscribir_en_campeonato(self.request.user, cat.campeonato):
            raise PermissionDenied("No tiene permiso para gestionar inscripciones en esta categoría.")
        return cat

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cat = self.object
        user = self.request.user
        es_staff = usuario_es_staff_asociacion(user)
        dojo_inst = obtener_dojo_instructor(user)

        inscripciones_qs = cat.inscripciones.select_related(
            'alumno_color', 'alumno_color__dojo', 'alumno_color__grado_actual',
            'alumno_dan', 'alumno_dan__dojo',
        ).order_by('orden_salida_inicial', 'id')

        # Si es instructor de otro dojo en un campeonato general, en la vista de inscripción
        # solo gestiona/elimina a sus propios alumnos (aunque vea el total de inscritos)
        if not es_staff and dojo_inst and cat.campeonato.ambito == 'GENERAL':
            mis_inscripciones = [
                i for i in inscripciones_qs
                if (i.dojo_obj and i.dojo_obj.id == dojo_inst.id)
            ]
        else:
            mis_inscripciones = list(inscripciones_qs)

        context.update({
            'puede_administrar': usuario_puede_administrar_campeonato(user, cat.campeonato),
            'inscripciones': mis_inscripciones if not usuario_puede_administrar_campeonato(user, cat.campeonato) else list(inscripciones_qs),
            'total_inscritos_categoria': inscripciones_qs.count(),
            'form_inscripcion': InscripcionCompetidorForm(user=user, categoria=cat),
            'rondas': cat.rondas.prefetch_related('actuaciones', 'enfrentamientos').all(),
            'resultados_historicos': cat.resultados_historicos.order_by('puesto'),
        })
        return context


class InscripcionCreateView(InstructorOrStaffRequiredMixin, View):
    """
    Inscribe a un competidor (AlumnoColor o Alumno DAN) verificando:
    1. Pertenencia del alumno al Dojo del instructor (anti-IDOR).
    2. Edad exacta por fecha de cumpleaños el día del campeonato.
    3. Consentimiento RGPD / LOPDGDD para menores.
    4. Mayoría de edad (>= 18 años) si la categoría es de Kumite.
    """

    def post(self, request, categoria_id):
        cat = get_object_or_404(
            CategoriaCampeonato.objects.select_related('campeonato'),
            pk=categoria_id,
        )
        if not usuario_puede_inscribir_en_campeonato(request.user, cat.campeonato):
            raise PermissionDenied("No tiene autorización para inscribir en este campeonato.")

        alumno_color_id = request.POST.get('alumno_color')
        alumno_dan_id = request.POST.get('alumno_dan')

        alumno_color = None
        alumno_dan = None

        if alumno_color_id:
            # Verificar estrictamente que el AlumnoColor pertenezca al ámbito permitido del usuario
            alumno_color = AlumnoColor.objects.for_user(request.user).filter(pk=alumno_color_id).first()
            if not alumno_color:
                raise PermissionDenied(
                    "Protección de Datos (RGPD): No puede inscribir un alumno de cinturón de color de otro Dojo."
                )

        if alumno_dan_id:
            from administracion.models import Alumno
            alumno_dan = get_object_or_404(Alumno, pk=alumno_dan_id)
            if not usuario_es_staff_asociacion(request.user):
                dojo_inst = obtener_dojo_instructor(request.user)
                if not dojo_inst or alumno_dan.dojo_id != dojo_inst.id:
                    raise PermissionDenied("Solo puede inscribir alumnos pertenecientes a su propio Dojo.")

        orden_siguiente = cat.inscripciones.count() + 1
        inscripcion = InscripcionCampeonato(
            categoria=cat,
            alumno_color=alumno_color,
            alumno_dan=alumno_dan,
            orden_salida_inicial=orden_siguiente,
            inscrito_por=request.user,
        )
        try:
            inscripcion.save()
            messages.success(
                request,
                f"Inscrito correctamente: {inscripcion.nombre_competidor} (Dorsal #{inscripcion.dorsal}).",
            )
        except ValidationError as exc:
            messages.error(request, f"Inscripción rechazada: {'; '.join(exc.messages)}")

        return redirect('campeonatos:categoria_detalle', pk=cat.pk)


class InscripcionDeleteView(InstructorOrStaffRequiredMixin, View):
    """Anula la inscripción de un competidor antes de que la categoría finalice."""

    def post(self, request, pk):
        inscripcion = get_object_or_404(
            InscripcionCampeonato.objects.select_related('categoria', 'categoria__campeonato'),
            pk=pk,
        )
        cat = inscripcion.categoria
        if cat.estado == 'FINALIZADA':
            messages.error(request, "No se pueden eliminar inscripciones de una categoría ya finalizada.")
            return redirect('campeonatos:categoria_detalle', pk=cat.pk)

        if not usuario_puede_administrar_campeonato(request.user, cat.campeonato):
            dojo_inst = obtener_dojo_instructor(request.user)
            if not dojo_inst or not inscripcion.dojo_obj or inscripcion.dojo_obj.id != dojo_inst.id:
                raise PermissionDenied("No tiene permiso para eliminar la inscripción de otro Dojo.")

        nombre = inscripcion.nombre_competidor
        inscripcion.delete()
        messages.success(request, f"Inscripción de {nombre} eliminada.")
        return redirect('campeonatos:categoria_detalle', pk=cat.pk)


class TatamiLiveView(LoginRequiredMixin, DetailView):
    """
    Panel Operativo de Tatami en Vivo (Móvil / Tablet Friendly).
    Muestra exclusivamente las categorías asignadas a este Tatami y los datos mínimos
    necesarios para llamar y puntuar al competidor (Dorsal, Nombre, Dojo y Cinturón).
    """
    model = Tatami
    template_name = 'campeonatos/tatami_live.html'
    context_object_name = 'tatami'
    pk_url_kwarg = 'tatami_id'

    def get_object(self, queryset=None):
        tatami = get_object_or_404(
            Tatami.objects.select_related('campeonato', 'juez_operador'),
            pk=self.kwargs['tatami_id'],
        )
        verificar_permiso_operacion_tatami(self.request.user, tatami)
        return tatami

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tatami = self.object
        categorias = list(
            tatami.categorias.prefetch_related(
                'inscripciones__alumno_color__dojo',
                'inscripciones__alumno_color__grado_actual',
                'inscripciones__alumno_dan__dojo',
                'rondas__actuaciones__inscripcion__alumno_color__dojo',
                'rondas__actuaciones__inscripcion__alumno_color__grado_actual',
                'rondas__actuaciones__inscripcion__alumno_dan__dojo',
                'rondas__enfrentamientos__aka_inscripcion__alumno_color__dojo',
                'rondas__enfrentamientos__aka_inscripcion__alumno_color__grado_actual',
                'rondas__enfrentamientos__aka_inscripcion__alumno_dan__dojo',
                'rondas__enfrentamientos__ao_inscripcion__alumno_color__dojo',
                'rondas__enfrentamientos__ao_inscripcion__alumno_color__grado_actual',
                'rondas__enfrentamientos__ao_inscripcion__alumno_dan__dojo',
                'resultados_historicos',
            ).order_by('orden_ejecucion', 'id')
        )

        cat_id_param = self.request.GET.get('categoria')
        categoria_activa = None
        if cat_id_param and cat_id_param.isdigit():
            categoria_activa = next((c for c in categorias if c.id == int(cat_id_param)), None)
        if not categoria_activa and categorias:
            categoria_activa = next((c for c in categorias if c.estado != 'FINALIZADA'), categorias[0])

        ronda_activa = None
        if categoria_activa:
            rondas_cat = list(categoria_activa.rondas.all())
            ronda_activa = next((r for r in rondas_cat if not r.cerrada), rondas_cat[-1] if rondas_cat else None)

        context.update({
            'campeonato': tatami.campeonato,
            'categorias_tatami': categorias,
            'categoria_activa': categoria_activa,
            'ronda_activa': ronda_activa,
            'rango_jueces': list(range(1, tatami.num_jueces_mesa + 1)),
            'puede_administrar': usuario_puede_administrar_campeonato(self.request.user, tatami.campeonato),
        })
        return context


class TatamiIniciarCategoriaView(LoginRequiredMixin, View):
    """Inicia la primera ronda de una categoría asignada al Tatami."""

    def post(self, request, tatami_id, categoria_id):
        tatami = get_object_or_404(Tatami.objects.select_related('campeonato'), pk=tatami_id)
        verificar_permiso_operacion_tatami(request.user, tatami)

        categoria = get_object_or_404(CategoriaCampeonato, pk=categoria_id, tatami=tatami)
        try:
            ronda = iniciar_competicion_categoria(categoria)
            messages.success(request, f"Iniciada '{ronda.nombre}' para {categoria.nombre}.")
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={categoria.id}")


class TatamiRegistrarPuntuacionView(LoginRequiredMixin, View):
    """Guarda las puntuaciones de los jueces para un competidor en la ronda activa del Tatami."""

    def post(self, request, tatami_id, actuacion_id):
        tatami = get_object_or_404(Tatami.objects.select_related('campeonato'), pk=tatami_id)
        verificar_permiso_operacion_tatami(request.user, tatami)

        actuacion = get_object_or_404(
            ActuacionPuntuacion.objects.select_related('ronda', 'ronda__categoria', 'inscripcion'),
            pk=actuacion_id,
            ronda__categoria__tatami=tatami,
        )
        if actuacion.ronda.cerrada or actuacion.ronda.categoria.estado == 'FINALIZADA':
            messages.error(request, "Esta ronda ya está cerrada y no admite cambios de puntuación.")
            return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={actuacion.ronda.categoria_id}")

        notas = []
        raw_notas = request.POST.getlist('notas_jueces')
        try:
            if raw_notas:
                for val in raw_notas:
                    if str(val).strip() != "":
                        n = Decimal(str(val).replace(',', '.'))
                        if n < Decimal('0.0') or n > Decimal('10.0'):
                            raise ValueError("Las notas deben estar entre 0.0 y 10.0.")
                        notas.append(n)
            else:
                for idx in range(1, tatami.num_jueces_mesa + 1):
                    val = request.POST.get(f'nota_juez_{idx}')
                    if val is not None and str(val).strip() != "":
                        n = Decimal(str(val).replace(',', '.'))
                        if n < Decimal('0.0') or n > Decimal('10.0'):
                            raise ValueError("Las notas deben estar entre 0.0 y 10.0.")
                        notas.append(n)

            if not notas:
                raise ValueError("Debe introducir al menos una puntuación válida.")

            actuacion.registrar_notas(notas)
            messages.success(
                request,
                f"Puntuación guardada para {actuacion.inscripcion.nombre_competidor}: Total {actuacion.nota_total} pts.",
            )
        except (InvalidOperation, ValueError) as exc:
            messages.error(request, f"Error en puntuación: {exc}")

        return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={actuacion.ronda.categoria_id}")


class TatamiRegistrarCombateView(LoginRequiredMixin, View):
    """
    Registra el resultado de un enfrentamiento 1 vs 1 (Banderas Aka/Ao para Kata o
    marcador de puntos para Kumite) en el Tatami.
    """

    def post(self, request, tatami_id, combate_id):
        tatami = get_object_or_404(Tatami.objects.select_related('campeonato'), pk=tatami_id)
        verificar_permiso_operacion_tatami(request.user, tatami)

        combate = get_object_or_404(
            EnfrentamientoBanderas.objects.select_related(
                'ronda', 'ronda__categoria', 'aka_inscripcion', 'ao_inscripcion'
            ),
            pk=combate_id,
            ronda__categoria__tatami=tatami,
        )
        if combate.ronda.cerrada or combate.ronda.categoria.estado == 'FINALIZADA':
            messages.error(request, "Esta ronda ya está cerrada.")
            return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={combate.ronda.categoria_id}")

        try:
            banderas_aka = int(request.POST.get('banderas_aka', 0) or 0)
            banderas_ao = int(request.POST.get('banderas_ao', 0) or 0)
            puntos_aka = int(request.POST.get('puntos_aka', 0) or 0)
            puntos_ao = int(request.POST.get('puntos_ao', 0) or 0)
            penalizaciones_aka = int(request.POST.get('penalizaciones_aka', 0) or 0)
            penalizaciones_ao = int(request.POST.get('penalizaciones_ao', 0) or 0)
            ganador_side = request.POST.get('ganador_side')  # 'AKA' o 'AO'

            combate.banderas_aka = max(0, banderas_aka)
            combate.banderas_ao = max(0, banderas_ao)
            combate.puntos_aka = max(0, puntos_aka)
            combate.puntos_ao = max(0, puntos_ao)
            combate.penalizaciones_aka = max(0, penalizaciones_aka)
            combate.penalizaciones_ao = max(0, penalizaciones_ao)

            if ganador_side == 'AKA':
                combate.ganador = combate.aka_inscripcion
            elif ganador_side == 'AO' and combate.ao_inscripcion:
                combate.ganador = combate.ao_inscripcion
            elif combate.ronda.categoria.modalidad == 'KUMITE':
                if puntos_aka > puntos_ao:
                    combate.ganador = combate.aka_inscripcion
                elif puntos_ao > puntos_aka and combate.ao_inscripcion:
                    combate.ganador = combate.ao_inscripcion
                else:
                    raise ValueError("En caso de empate a puntos en Kumite debe indicar el ganador (Hantei / Senshu).")
            else:
                if banderas_aka > banderas_ao:
                    combate.ganador = combate.aka_inscripcion
                elif banderas_ao > banderas_aka and combate.ao_inscripcion:
                    combate.ganador = combate.ao_inscripcion
                else:
                    raise ValueError("El número de banderas no puede quedar empatado; indique un ganador.")

            combate.finalizado = True
            combate.save()
            messages.success(
                request,
                f"Combate #{combate.orden_combate} registrado. Ganador: {combate.ganador.nombre_competidor}.",
            )
        except ValueError as exc:
            messages.error(request, f"No se pudo guardar el combate: {exc}")

        return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={combate.ronda.categoria_id}")


class TatamiCerrarRondaView(LoginRequiredMixin, View):
    """
    Cierra la ronda actual de la categoría en el Tatami:
    - Calcula automáticamente el corte Top N (o genera ronda de desempate si hay empate).
    - O avanza la eliminatoria de banderas/kumite.
    - O consolida el podio final en ResultadoHistorico.
    """

    def post(self, request, tatami_id, ronda_id):
        tatami = get_object_or_404(Tatami.objects.select_related('campeonato'), pk=tatami_id)
        verificar_permiso_operacion_tatami(request.user, tatami)

        ronda = get_object_or_404(
            RondaCategoria.objects.select_related('categoria', 'categoria__campeonato'),
            pk=ronda_id,
            categoria__tatami=tatami,
        )
        try:
            if ronda.categoria.sistema == 'PUNTOS':
                resultado = cerrar_y_avanzar_ronda_puntuacion(ronda)
            else:
                resultado = cerrar_y_avanzar_ronda_banderas(ronda)

            if resultado['estado'] in ('DESEMPATE_CORTE', 'DESEMPATE_PODIO'):
                messages.warning(request, resultado['mensaje'])
            else:
                messages.success(request, resultado['mensaje'])
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(f"{reverse('campeonatos:tatami_live', kwargs={'tatami_id': tatami.id})}?categoria={ronda.categoria_id}")


class CampeonatosHistoricoView(LoginRequiredMixin, ListView):
    """
    Consulta del registro histórico inmutable de campeonatos y podios.
    """
    model = ResultadoHistorico
    template_name = 'campeonatos/historico.html'
    context_object_name = 'resultados'

    def get_queryset(self):
        campeonatos_visibles = Campeonato.objects.visibles_para(self.request.user)
        qs = (
            ResultadoHistorico.objects.filter(campeonato__in=campeonatos_visibles)
            .select_related('campeonato', 'categoria')
            .order_by('-campeonato__fecha_inicio', 'categoria__orden_ejecucion', 'puesto')
        )
        camp_id = self.request.GET.get('campeonato')
        if camp_id and camp_id.isdigit():
            qs = qs.filter(campeonato_id=int(camp_id))

        modalidad = self.request.GET.get('modalidad')
        if modalidad in ('KATA', 'KUMITE'):
            qs = qs.filter(modalidad_snapshot=modalidad)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campeonatos_disponibles'] = Campeonato.objects.visibles_para(self.request.user)
        context['campeonato_seleccionado'] = self.request.GET.get('campeonato', '')
        context['modalidad_seleccionada'] = self.request.GET.get('modalidad', '')
        return context


class CampeonatosAyudaView(LoginRequiredMixin, TemplateView):
    """
    Centro de Ayuda y Manual Operativo del Módulo de Campeonatos.
    Adaptado por perfiles (Anotadores/Jueces de Mesa, Instructores de Dojo y
    Dirección del Torneo/Staff) con buscador de dudas frecuentes (FAQ).
    """
    template_name = 'campeonatos/ayuda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        es_juez = es_usuario_juez_efimero(user)
        es_staff = usuario_es_staff_asociacion(user)
        dojo_inst = obtener_dojo_instructor(user)

        # Determinar la sección destacada por defecto según el rol o parámetro ?rol=
        rol_param = self.request.GET.get('rol', '').lower()
        if rol_param in ('juez', 'instructor', 'direccion'):
            rol_activo = rol_param
        elif es_juez:
            rol_activo = 'juez'
        elif es_staff:
            rol_activo = 'direccion'
        elif dojo_inst is not None:
            rol_activo = 'instructor'
        else:
            rol_activo = 'juez'

        context.update({
            'rol_activo': rol_activo,
            'es_juez_efimero': es_juez,
            'tatami_activo': obtener_tatamis_activos_juez(user).first() if es_juez else None,
            'es_staff': es_staff,
            'es_instructor': dojo_inst is not None,
        })
        return context

