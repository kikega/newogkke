"""
Modelos de la aplicación de Gestión Integral de Campeonatos (Kata y Kumite).
Incluye soporte para torneos locales (Dojo) y generales (Asociación),
tatamis con jueces efímeros limitados a las fechas del evento, rondas de puntuación,
rondas de desempate, eliminatorias de banderas/kumite e histórico inmutable.
"""
import datetime
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from usuarios.models import Usuario
from administracion.models import (
    Dojo,
    Alumno,
    AlumnoColor,
    GradoKyu,
    calcular_edad_en_fecha,
)


class CampeonatoQuerySet(models.QuerySet):
    """QuerySet con filtrado de visibilidad de campeonatos según rol."""

    def visibles_para(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_staff or user.is_superuser:
            return self.all()

        # Verificar si es juez operador de algún tatami activo en fecha
        hoy = datetime.date.today()
        tatamis_juez = self.filter(
            tatamis__juez_operador=user,
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy,
        ).exclude(estado='FINALIZADO')

        try:
            alumno = Alumno.objects.select_related('dojo').get(usuario=user)
            return (
                self.filter(
                    models.Q(ambito='GENERAL')
                    | models.Q(ambito='LOCAL', dojo_organizador=alumno.dojo)
                    | models.Q(pk__in=tatamis_juez.values('pk'))
                ).distinct()
            )
        except Alumno.DoesNotExist:
            return tatamis_juez.distinct()


CampeonatoManager = models.Manager.from_queryset(CampeonatoQuerySet)


class Campeonato(models.Model):
    """
    Torneo de Karate de ámbito Local (un solo Dojo) o General (Asociación OGKKE).
    """
    objects = CampeonatoManager()

    AMBITO_CHOICES = (
        ('LOCAL', 'Local (Dojo único)'),
        ('GENERAL', 'General (Asociación OGKKE)'),
    )
    SISTEMA_CHOICES = (
        ('PUNTOS', 'Puntuación Numérica'),
        ('BANDERAS', 'Banderas / Eliminatoria Directa (Aka vs Ao)'),
    )
    ESTADO_CHOICES = (
        ('BORRADOR', 'Borrador / Configuración'),
        ('INSCRIPCION', 'Inscripción Abierta'),
        ('EN_CURSO', 'En Curso (Tatamis Activos)'),
        ('FINALIZADO', 'Finalizado (Histórico Consolidado)'),
    )

    nombre = models.CharField(max_length=150, verbose_name="Nombre del Campeonato")
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    ambito = models.CharField(
        max_length=15,
        choices=AMBITO_CHOICES,
        default='GENERAL',
        verbose_name="Ámbito del Torneo"
    )
    dojo_organizador = models.ForeignKey(
        Dojo,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="campeonatos_organizados",
        verbose_name="Dojo Organizador",
        help_text="Obligatorio para campeonatos de ámbito Local."
    )
    sistema_puntuacion_default = models.CharField(
        max_length=15,
        choices=SISTEMA_CHOICES,
        default='PUNTOS',
        verbose_name="Sistema de evaluación por defecto"
    )
    fecha_inicio = models.DateField(
        db_index=True,
        verbose_name="Fecha de inicio",
        help_text="Fecha oficial usada también para el cálculo exacto de edad por cumpleaños."
    )
    fecha_fin = models.DateField(
        db_index=True,
        verbose_name="Fecha de clausura",
        help_text="Una vez superada esta fecha, los usuarios efímeros de tatami no podrán iniciar sesión."
    )
    lugar = models.CharField(max_length=120, verbose_name="Pabellón / Lugar")
    ciudad = models.CharField(max_length=60, verbose_name="Ciudad")
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='BORRADOR',
        db_index=True,
        verbose_name="Estado"
    )
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campeonatos_creados"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Campeonato"
        verbose_name_plural = "Campeonatos"
        ordering = ['-fecha_inicio', '-id']

    def _generate_unique_slug(self):
        base_slug = slugify(f"{self.nombre}-{self.fecha_inicio.year if self.fecha_inicio else ''}") or "torneo"
        candidate = base_slug
        counter = 2
        qs = Campeonato.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    def esta_en_fechas_activas(self, fecha_ref=None):
        """
        Indica si la fecha de referencia (por defecto hoy) está dentro del rango
        [fecha_inicio, fecha_fin] y el torneo no está finalizado.
        """
        ref = fecha_ref or datetime.date.today()
        if self.estado == 'FINALIZADO':
            return False
        return self.fecha_inicio <= ref <= self.fecha_fin

    def calcular_edad_competidor(self, fecha_nacimiento):
        """
        Calcula la edad exacta del competidor el día de inicio del campeonato
        según su fecha de cumpleaños.
        """
        return calcular_edad_en_fecha(fecha_nacimiento, self.fecha_inicio)

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                'fecha_fin': "La fecha de clausura no puede ser anterior a la fecha de inicio."
            })
        if self.ambito == 'LOCAL' and not self.dojo_organizador:
            raise ValidationError({
                'dojo_organizador': "Los campeonatos de ámbito Local deben tener un Dojo organizador asignado."
            })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.fecha_inicio})"


class Tatami(models.Model):
    """
    Área de competición dentro de un Campeonato, con asignación de un usuario
    operador/juez efímero cuyos permisos caducan al finalizar las fechas del torneo.
    """
    objects = models.Manager()

    campeonato = models.ForeignKey(
        Campeonato,
        on_delete=models.CASCADE,
        related_name="tatamis",
        verbose_name="Campeonato"
    )
    numero = models.PositiveSmallIntegerField(verbose_name="Número de Tatami")
    nombre = models.CharField(
        max_length=80,
        verbose_name="Nombre identificativo",
        help_text="Ej. Tatami 1 - Central"
    )
    juez_operador = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tatamis_asignados",
        verbose_name="Usuario Juez / Mesa asignado"
    )
    num_jueces_mesa = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Número de jueces puntuadores",
        help_text="Habitualmente 3 o 5 jueces."
    )

    class Meta:
        verbose_name = "Tatami"
        verbose_name_plural = "Tatamis"
        unique_together = (('campeonato', 'numero'),)
        ordering = ['campeonato', 'numero']

    def acceso_operador_vigente(self, fecha_ref=None):
        """
        El operador de mesa solo tiene acceso durante las fechas del campeonato
        y mientras el campeonato no haya finalizado.
        """
        return self.campeonato.esta_en_fechas_activas(fecha_ref=fecha_ref)

    def __str__(self):
        return f"Tatami {self.numero} ({self.nombre}) · {self.campeonato.nombre}"


class CategoriaCampeonato(models.Model):
    """
    Categoría de competición dentro de un Campeonato (definida por modalidad,
    rango de edad el día del torneo, género y rango de cinturones).
    RESTRICCIÓN LEGAL/DEPORTIVA: Kumite solo está permitido para mayores de edad (>= 18 años).
    """
    objects = models.Manager()

    MODALIDAD_CHOICES = (
        ('KATA', 'Kata (Técnica Individual)'),
        ('KUMITE', 'Kumite (Combate - Solo Mayores de 18 años)'),
    )
    GENERO_CHOICES = (
        ('X', 'Mixto'),
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    )
    SISTEMA_CHOICES = (
        ('PUNTOS', 'Puntuación (Pasan los N mejores)'),
        ('BANDERAS', 'Eliminatoria Directa 1 vs 1 (Aka / Ao)'),
    )
    ESTADO_CHOICES = (
        ('PENDIENTE', 'Pendiente de iniciar'),
        ('EN_CURSO', 'En disputa en Tatami'),
        ('FINALIZADA', 'Finalizada (Acta cerrada)'),
    )

    campeonato = models.ForeignKey(
        Campeonato,
        on_delete=models.CASCADE,
        related_name="categorias",
        verbose_name="Campeonato"
    )
    tatami = models.ForeignKey(
        Tatami,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categorias",
        verbose_name="Tatami asignado"
    )
    nombre = models.CharField(
        max_length=120,
        verbose_name="Nombre de la Categoría",
        help_text="Ej. Alevín Mixto Cintos de Color (8-9 años)"
    )
    modalidad = models.CharField(
        max_length=10,
        choices=MODALIDAD_CHOICES,
        default='KATA',
        verbose_name="Modalidad"
    )
    genero = models.CharField(
        max_length=1,
        choices=GENERO_CHOICES,
        default='X',
        verbose_name="Género"
    )
    edad_min = models.PositiveSmallIntegerField(
        default=6,
        verbose_name="Edad mínima (en fecha del torneo)"
    )
    edad_max = models.PositiveSmallIntegerField(
        default=99,
        verbose_name="Edad máxima (en fecha del torneo)"
    )
    admite_cintos_color = models.BooleanField(
        default=True,
        verbose_name="Admite Cinturones de Color (Kyu)"
    )
    admite_cintos_negros = models.BooleanField(
        default=False,
        verbose_name="Admite Cinturones Negros (DAN)"
    )
    grado_kyu_min = models.ForeignKey(
        GradoKyu,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Grado Kyu mínimo"
    )
    grado_kyu_max = models.ForeignKey(
        GradoKyu,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Grado Kyu máximo"
    )
    grado_dan_min = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Grado DAN mínimo"
    )
    grado_dan_max = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Grado DAN máximo"
    )
    sistema = models.CharField(
        max_length=15,
        choices=SISTEMA_CHOICES,
        default='PUNTOS',
        verbose_name="Sistema de Competición"
    )
    clasificados_siguiente_ronda = models.PositiveSmallIntegerField(
        default=4,
        verbose_name="Clasificados al corte (Top N)",
        help_text="Número de competidores con mayor nota que pasan a la siguiente ronda."
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    orden_ejecucion = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Orden de salida en el Tatami"
    )

    class Meta:
        verbose_name = "Categoría de Campeonato"
        verbose_name_plural = "Categorías de Campeonato"
        ordering = ['orden_ejecucion', 'edad_min', 'nombre']

    def clean(self):
        super().clean()
        if self.edad_min is not None and self.edad_max is not None and self.edad_max < self.edad_min:
            raise ValidationError({
                'edad_max': "La edad máxima no puede ser inferior a la edad mínima."
            })

        # Regla de negocio obligatoria: Kumite solo para mayores de edad (>= 18 años)
        if self.modalidad == 'KUMITE':
            if self.edad_min is None or self.edad_min < 18:
                raise ValidationError({
                    'edad_min': "La modalidad de Kumite está permitida exclusivamente para mayores de edad (mínimo 18 años)."
                })
            # Kumite siempre se disputa por enfrentamientos 1 contra 1 (Aka vs Ao)
            self.sistema = 'BANDERAS'

        if (
            self.grado_kyu_min
            and self.grado_kyu_max
            and self.grado_kyu_max.orden < self.grado_kyu_min.orden
        ):
            raise ValidationError({
                'grado_kyu_max': "El grado Kyu máximo no puede ser inferior en jerarquía al grado Kyu mínimo."
            })

        if self.tatami and self.campeonato_id and self.tatami.campeonato_id != self.campeonato_id:
            raise ValidationError({
                'tatami': "El tatami asignado debe pertenecer al mismo campeonato."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} · {self.get_modalidad_display()} ({self.campeonato.nombre})"


class InscripcionCampeonato(models.Model):
    """
    Inscripción validada de un competidor (AlumnoColor o Alumno DAN) en una categoría.
    Valida edad exacta por fecha de cumpleaños el día del torneo, consentimiento RGPD
    para menores y prohibición de menores en Kumite.
    """
    objects = models.Manager()

    categoria = models.ForeignKey(
        CategoriaCampeonato,
        on_delete=models.CASCADE,
        related_name="inscripciones",
        verbose_name="Categoría"
    )
    alumno_color = models.ForeignKey(
        AlumnoColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inscripciones_campeonato",
        verbose_name="Competidor Cinturón de Color"
    )
    alumno_dan = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inscripciones_campeonato",
        verbose_name="Competidor Cinturón Negro"
    )
    dorsal = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Dorsal"
    )
    orden_salida_inicial = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Orden de salida"
    )
    inscrito_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Inscrito por"
    )
    descalificado = models.BooleanField(
        default=False,
        verbose_name="Descalificado / No presentado"
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inscripción en Campeonato"
        verbose_name_plural = "Inscripciones en Campeonatos"
        ordering = ['orden_salida_inicial', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'alumno_color'],
                condition=models.Q(alumno_color__isnull=False),
                name='uniq_inscripcion_categoria_alumno_color'
            ),
            models.UniqueConstraint(
                fields=['categoria', 'alumno_dan'],
                condition=models.Q(alumno_dan__isnull=False),
                name='uniq_inscripcion_categoria_alumno_dan'
            ),
        ]

    @property
    def competidor_obj(self):
        return self.alumno_color or self.alumno_dan

    @property
    def nombre_competidor(self):
        comp = self.competidor_obj
        return f"{comp.apellidos}, {comp.nombre}" if comp else "Desconocido"

    @property
    def dojo_obj(self):
        comp = self.competidor_obj
        return comp.dojo if comp else None

    @property
    def dojo_nombre(self):
        dojo = self.dojo_obj
        return dojo.nombre if dojo else "-"

    @property
    def grado_mostrable(self):
        if self.alumno_color:
            return self.alumno_color.grado_actual.nombre
        if self.alumno_dan:
            return f"{self.alumno_dan.grado}º DAN" if self.alumno_dan.grado else "Cinturón Negro"
        return "-"

    @property
    def fecha_nacimiento_competidor(self):
        comp = self.competidor_obj
        return comp.fecha_nacimiento if comp else None

    @property
    def edad_en_torneo(self):
        fecha_nac = self.fecha_nacimiento_competidor
        if not fecha_nac or not self.categoria_id:
            return None
        return self.categoria.campeonato.calcular_edad_competidor(fecha_nac)

    def clean(self):
        super().clean()
        if bool(self.alumno_color) == bool(self.alumno_dan):
            raise ValidationError(
                "Debe seleccionar exactamente un competidor (Alumno de Color o Cinturón Negro)."
            )

        if not self.categoria_id:
            return

        campeonato = self.categoria.campeonato
        comp = self.competidor_obj

        if not comp.activo:
            raise ValidationError("No se puede inscribir a un alumno que no está en alta activa.")

        # Validar ámbito Local vs General
        if campeonato.ambito == 'LOCAL' and campeonato.dojo_organizador_id != comp.dojo_id:
            raise ValidationError(
                f"Este campeonato es de ámbito Local exclusivo para {campeonato.dojo_organizador.nombre}."
            )

        # Validar fecha de nacimiento obligatoria para cálculo de edad el día del torneo
        if not comp.fecha_nacimiento:
            raise ValidationError(
                "El competidor debe tener registrada su fecha de nacimiento para verificar su categoría de edad el día del torneo."
            )

        edad_torneo = campeonato.calcular_edad_competidor(comp.fecha_nacimiento)

        # Prohibición estricta de menores de 18 años en Kumite
        if self.categoria.modalidad == 'KUMITE' and edad_torneo < 18:
            raise ValidationError(
                f"El competidor tiene {edad_torneo} años en la fecha del torneo ({campeonato.fecha_inicio}). "
                "La modalidad de Kumite es exclusivamente para mayores de edad (18 años o más)."
            )

        # Validar rango de edad de la categoría según cumpleaños a fecha del torneo
        if not (self.categoria.edad_min <= edad_torneo <= self.categoria.edad_max):
            raise ValidationError(
                f"Edad fuera de rango: el competidor tendrá {edad_torneo} años el día del campeonato "
                f"({campeonato.fecha_inicio}), pero la categoría '{self.categoria.nombre}' "
                f"requiere entre {self.categoria.edad_min} y {self.categoria.edad_max} años."
            )

        # Validaciones específicas de Cinturones de Color y Protección de Menores (RGPD / LOPDGDD)
        if self.alumno_color:
            if not self.categoria.admite_cintos_color:
                raise ValidationError("Esta categoría no admite cinturones de color (Kyu).")

            # Si es menor de 14 años (o menor de edad), verificar consentimiento paterno y de campeonatos
            if edad_torneo < 14 or self.alumno_color.es_menor_14:
                if not (
                    self.alumno_color.consentimiento_firmado
                    and self.alumno_color.consentimiento_campeonatos
                    and self.alumno_color.fecha_firma_consentimiento
                ):
                    raise ValidationError(
                        "Protección de Menores (LOPDGDD): El alumno es menor de 14 años y no dispone "
                        "de autorización paterna y de campeonatos firmada y validada."
                    )
            elif edad_torneo < 18:
                if not (
                    self.alumno_color.consentimiento_firmado
                    and self.alumno_color.consentimiento_campeonatos
                ):
                    raise ValidationError(
                        "Protección de Menores: El competidor menor de 18 años requiere autorización "
                        "firmada para participar en campeonatos."
                    )

            orden_kyu = self.alumno_color.grado_actual.orden
            if self.categoria.grado_kyu_min and orden_kyu < self.categoria.grado_kyu_min.orden:
                raise ValidationError(
                    f"El grado del alumno ({self.alumno_color.grado_actual.nombre}) es inferior al mínimo "
                    f"de la categoría ({self.categoria.grado_kyu_min.nombre})."
                )
            if self.categoria.grado_kyu_max and orden_kyu > self.categoria.grado_kyu_max.orden:
                raise ValidationError(
                    f"El grado del alumno ({self.alumno_color.grado_actual.nombre}) supera el máximo "
                    f"de la categoría ({self.categoria.grado_kyu_max.nombre})."
                )

        if self.alumno_dan:
            if not self.categoria.admite_cintos_negros:
                raise ValidationError("Esta categoría no admite cinturones negros (DAN).")
            grado_dan = self.alumno_dan.grado or 1
            if self.categoria.grado_dan_min and grado_dan < self.categoria.grado_dan_min:
                raise ValidationError(
                    f"El grado DAN del alumno ({grado_dan}º DAN) es inferior al mínimo requerido ({self.categoria.grado_dan_min}º DAN)."
                )
            if self.categoria.grado_dan_max and grado_dan > self.categoria.grado_dan_max:
                raise ValidationError(
                    f"El grado DAN del alumno ({grado_dan}º DAN) supera el máximo permitido ({self.categoria.grado_dan_max}º DAN)."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.dorsal and self.categoria_id:
            existentes = InscripcionCampeonato.objects.filter(
                categoria__campeonato=self.categoria.campeonato
            ).count()
            self.dorsal = existentes + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.dorsal or '-'} {self.nombre_competidor} ({self.dojo_nombre})"


class RondaCategoria(models.Model):
    """
    Fase o ronda dentro de una Categoría (ej. Ronda Clasificatoria, Ronda de Desempate,
    Cuartos, Semifinal, Final).
    """
    objects = models.Manager()

    categoria = models.ForeignKey(
        CategoriaCampeonato,
        on_delete=models.CASCADE,
        related_name="rondas",
        verbose_name="Categoría"
    )
    numero = models.PositiveSmallIntegerField(verbose_name="Número de ronda")
    nombre = models.CharField(max_length=80, verbose_name="Nombre de la ronda")
    es_final = models.BooleanField(default=False, verbose_name="Es ronda final")
    es_desempate = models.BooleanField(
        default=False,
        verbose_name="Es ronda de desempate",
        help_text="Generada automáticamente cuando existe empate en los puestos de corte o medalla."
    )
    cerrada = models.BooleanField(default=False, verbose_name="Ronda cerrada")

    class Meta:
        verbose_name = "Ronda de Categoría"
        verbose_name_plural = "Rondas de Categoría"
        unique_together = (('categoria', 'numero'),)
        ordering = ['categoria', 'numero']

    def __str__(self):
        return f"{self.categoria.nombre} · Ronda {self.numero}: {self.nombre}"


class ActuacionPuntuacion(models.Model):
    """
    Actuación individual y calificación en sistema de Puntuación numérica (Kata).
    """
    objects = models.Manager()

    ronda = models.ForeignKey(
        RondaCategoria,
        on_delete=models.CASCADE,
        related_name="actuaciones",
        verbose_name="Ronda"
    )
    inscripcion = models.ForeignKey(
        InscripcionCampeonato,
        on_delete=models.CASCADE,
        related_name="actuaciones_puntuacion",
        verbose_name="Competidor inscrito"
    )
    orden_salida = models.PositiveSmallIntegerField(default=1, verbose_name="Orden de salida")
    notas_jueces = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Notas individuales de los jueces"
    )
    nota_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Puntuación Total"
    )
    nota_media = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Media"
    )
    evaluado = models.BooleanField(default=False, verbose_name="Evaluado")
    clasificado = models.BooleanField(default=False, verbose_name="Clasificado a siguiente fase")

    class Meta:
        verbose_name = "Actuación de Puntuación"
        verbose_name_plural = "Actuaciones de Puntuación"
        unique_together = (('ronda', 'inscripcion'),)
        ordering = ['orden_salida', 'id']

    def registrar_notas(self, lista_notas):
        """
        Calcula y persiste la suma total y media a partir de las notas de los jueces.
        """
        limpias = [Decimal(str(n)).quantize(Decimal('0.01')) for n in lista_notas if n is not None]
        self.notas_jueces = [float(n) for n in limpias]
        if limpias:
            total = sum(limpias, Decimal('0.00'))
            self.nota_total = total.quantize(Decimal('0.01'))
            self.nota_media = (total / Decimal(len(limpias))).quantize(Decimal('0.01'))
            self.evaluado = True
        else:
            self.nota_total = Decimal('0.00')
            self.nota_media = Decimal('0.00')
            self.evaluado = False
        self.save()

    def __str__(self):
        return f"{self.inscripcion.nombre_competidor} · {self.nota_total} pts ({self.ronda.nombre})"


class EnfrentamientoBanderas(models.Model):
    """
    Cruce 1 contra 1 (Aka / Rojo vs Ao / Azul) para Kata por Banderas o Kumite.
    """
    objects = models.Manager()

    ronda = models.ForeignKey(
        RondaCategoria,
        on_delete=models.CASCADE,
        related_name="enfrentamientos",
        verbose_name="Ronda"
    )
    orden_combate = models.PositiveSmallIntegerField(default=1, verbose_name="Número de cruce")
    aka_inscripcion = models.ForeignKey(
        InscripcionCampeonato,
        on_delete=models.CASCADE,
        related_name="combates_aka",
        verbose_name="Aka (Rojo)"
    )
    ao_inscripcion = models.ForeignKey(
        InscripcionCampeonato,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="combates_ao",
        verbose_name="Ao (Azul) — Vacío si pasa por Bye"
    )
    banderas_aka = models.PositiveSmallIntegerField(default=0, verbose_name="Banderas Aka (Rojo)")
    banderas_ao = models.PositiveSmallIntegerField(default=0, verbose_name="Banderas Ao (Azul)")
    puntos_aka = models.PositiveSmallIntegerField(default=0, verbose_name="Puntos Kumite Aka")
    puntos_ao = models.PositiveSmallIntegerField(default=0, verbose_name="Puntos Kumite Ao")
    penalizaciones_aka = models.PositiveSmallIntegerField(default=0, verbose_name="Faltas Aka")
    penalizaciones_ao = models.PositiveSmallIntegerField(default=0, verbose_name="Faltas Ao")
    ganador = models.ForeignKey(
        InscripcionCampeonato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="combates_ganados",
        verbose_name="Ganador del enfrentamiento"
    )
    es_tercer_puesto = models.BooleanField(default=False, verbose_name="Combate por 3º puesto")
    finalizado = models.BooleanField(default=False, verbose_name="Finalizado")

    class Meta:
        verbose_name = "Enfrentamiento (Aka vs Ao)"
        verbose_name_plural = "Enfrentamientos (Aka vs Ao)"
        ordering = ['orden_combate', 'id']

    @property
    def marcador_resumen(self):
        if not self.finalizado:
            return "Pendiente"
        if self.ao_inscripcion is None:
            return "Pase directo (Bye)"
        if self.ronda.categoria.modalidad == 'KUMITE':
            return f"{self.puntos_aka} - {self.puntos_ao} pts"
        return f"{self.banderas_aka} - {self.banderas_ao} banderas"

    def __str__(self):
        ao_name = self.ao_inscripcion.nombre_competidor if self.ao_inscripcion else "BYE"
        return f"#{self.orden_combate}: {self.aka_inscripcion.nombre_competidor} (Aka) vs {ao_name} (Ao)"


class ResultadoHistorico(models.Model):
    """
    Registro histórico inmutable de clasificaciones y podios de un Campeonato.
    Almacena instantánea (snapshot) del nombre, dojo y grado que ostentaba el
    competidor el día del torneo.
    """
    objects = models.Manager()

    PUESTO_CHOICES = (
        (1, '1º Clasificado (Oro)'),
        (2, '2º Clasificado (Plata)'),
        (3, '3º Clasificado (Bronce)'),
        (4, '4º Clasificado (Finalista)'),
    )

    campeonato = models.ForeignKey(
        Campeonato,
        on_delete=models.PROTECT,
        related_name="resultados_historicos",
        verbose_name="Campeonato"
    )
    categoria = models.ForeignKey(
        CategoriaCampeonato,
        on_delete=models.PROTECT,
        related_name="resultados_historicos",
        verbose_name="Categoría"
    )
    puesto = models.PositiveSmallIntegerField(choices=PUESTO_CHOICES, verbose_name="Puesto")
    inscripcion = models.ForeignKey(
        InscripcionCampeonato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Inscripción original"
    )
    nombre_competidor_snapshot = models.CharField(max_length=140, verbose_name="Competidor")
    dojo_nombre_snapshot = models.CharField(max_length=100, verbose_name="Dojo")
    grado_snapshot = models.CharField(max_length=50, verbose_name="Grado en el torneo")
    modalidad_snapshot = models.CharField(max_length=20, default="KATA", verbose_name="Modalidad")
    puntuacion_final_snapshot = models.CharField(
        max_length=60,
        blank=True,
        default="",
        verbose_name="Marca / Resultado final"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resultado Histórico de Campeonato"
        verbose_name_plural = "Resultados Históricos de Campeonatos"
        ordering = ['campeonato', 'categoria', 'puesto']

    def __str__(self):
        return f"{self.get_puesto_display()} · {self.nombre_competidor_snapshot} ({self.categoria.nombre})"
