"""
Modelos de administración
"""
# Python
import datetime
import re
import uuid

# Django
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.utils.text import slugify

# Importamos el modelo de Usuario
from usuarios.models import Usuario


def calcular_edad_en_fecha(fecha_nacimiento, fecha_referencia=None):
    """
    Calcula la edad exacta en años cumplidos a una fecha de referencia dada
    (por defecto hoy) en base a la fecha exacta de cumpleaños.
    """
    if not fecha_nacimiento:
        return 0
    ref = fecha_referencia or datetime.date.today()
    return ref.year - fecha_nacimiento.year - (
        (ref.month, ref.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9a-fA-F]{6}$',
    message="Introduce un color hexadecimal válido en formato #RRGGBB (ej. #c89d3c)."
)

DOMAIN_REGEX = re.compile(
    r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$'
)


def normalizar_dominio(valor):
    """
    Limpia y normaliza un nombre de dominio eliminando protocolo, puerto, rutas y prefijo www.
    Devuelve None si la cadena queda vacía.
    """
    if not valor:
        return None
    limpio = str(valor).strip().lower()
    limpio = re.sub(r'^https?://', '', limpio)
    limpio = limpio.split('/')[0].split('?')[0].split(':')[0].strip('.')
    if limpio.startswith('www.'):
        limpio = limpio[4:]
    return limpio or None


class DojoScopedQuerySet(models.QuerySet):
    """
    QuerySet base para entidades cuyo ámbito de responsabilidad pertenece a un Dojo local.
    Garantiza aislamiento multi-tenant al filtrar por Dojo o por request.current_dojo.
    """

    def for_dojo(self, dojo_or_request):
        if dojo_or_request is None:
            return self.none()
        dojo = getattr(dojo_or_request, 'current_dojo', dojo_or_request)
        if dojo is None:
            return self.none()
        if isinstance(dojo, int):
            return self.filter(dojo_id=dojo)
        return self.filter(dojo=dojo)


DojoScopedManager = models.Manager.from_queryset(DojoScopedQuerySet)


class Dojo(models.Model):
    """
    Modelo que representa un gimnasio de la asociación y su configuración
    de portal autónomo / dominio propio (arquitectura Core + Dojos locales).
    """
    objects = models.Manager()

    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    direccion = models.CharField(max_length=100, verbose_name="Dirección")
    poblacion = models.CharField(max_length=100, verbose_name="Población")
    provincia = models.CharField(max_length=100, verbose_name="Provincia")
    codigo_postal = models.CharField(max_length=5, verbose_name="Código Postal")

    # Identidad digital, subdominio automático y dominio propio
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Identificador URL (slug)",
        help_text="Se genera automáticamente a partir del nombre y define el subdominio base (<slug>.ogkke.es)."
    )
    dominio_personalizado = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Dominio propio",
        help_text="Dominio personalizado sin https:// (ej. karatebudokan.es)."
    )
    sitio_activo = models.BooleanField(
        default=True,
        verbose_name="Portal del Dojo activo",
        help_text="Habilita el portal web propio y la emisión automática de certificados TLS para este Dojo."
    )
    color_primario = models.CharField(
        max_length=7,
        default="#c89d3c",
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name="Color de marca (Hex)",
        help_text="Color de acento personalizado para el portal de este Dojo."
    )
    logo = models.ImageField(
        upload_to='dojos/logos/%Y/%m',
        blank=True,
        null=True,
        verbose_name="Escudo / Logo del Dojo",
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    lema = models.CharField(
        max_length=180,
        blank=True,
        default="",
        verbose_name="Lema o subtítulo"
    )
    descripcion_publica = models.TextField(
        blank=True,
        default="",
        verbose_name="Presentación del Dojo",
        help_text="Texto público de presentación del centro en su portal."
    )
    horario_resumen = models.TextField(
        blank=True,
        default="",
        verbose_name="Horarios de entrenamiento",
        help_text="Días y franjas horarias de las clases del Dojo."
    )
    telefono_contacto = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono de contacto"
    )
    email_contacto = models.EmailField(
        blank=True,
        default="",
        verbose_name="Email público del Dojo"
    )

    class Meta:
        verbose_name = "Dojo"
        verbose_name_plural = "Dojos"
        ordering = ['nombre']

    def _generate_unique_slug(self):
        base_slug = slugify(self.nombre) or "dojo"
        candidate = base_slug
        counter = 2
        qs = Dojo.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    def clean(self):
        super().clean()
        if not self.slug and self.nombre:
            self.slug = self._generate_unique_slug()
        elif self.slug:
            self.slug = slugify(self.slug)

        self.dominio_personalizado = normalizar_dominio(self.dominio_personalizado)
        if self.dominio_personalizado:
            if not DOMAIN_REGEX.match(self.dominio_personalizado):
                raise ValidationError({
                    'dominio_personalizado': "Introduce un dominio válido (ej. karatebudokan.es)."
                })
            base_domain = getattr(settings, 'DOJO_BASE_DOMAIN', 'ogkke.es').lower()
            core_hosts = {h.lower() for h in getattr(settings, 'CORE_HOSTS', [base_domain, f"www.{base_domain}"])}
            if self.dominio_personalizado in core_hosts:
                raise ValidationError({
                    'dominio_personalizado': "El dominio propio del Dojo no puede coincidir con el dominio central de OGKKE."
                })

        if self.color_primario:
            self.color_primario = self.color_primario.strip().lower()
            if not self.color_primario.startswith('#'):
                self.color_primario = f"#{self.color_primario}"
            HEX_COLOR_VALIDATOR(self.color_primario)
        else:
            self.color_primario = "#c89d3c"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        self.dominio_personalizado = normalizar_dominio(self.dominio_personalizado)
        if not self.color_primario:
            self.color_primario = "#c89d3c"
        super().save(*args, **kwargs)

    @property
    def subdominio_oficial(self):
        base_domain = getattr(settings, 'DOJO_BASE_DOMAIN', 'ogkke.es')
        return f"{self.slug}.{base_domain}" if self.slug else base_domain

    @property
    def dominio_principal(self):
        return self.dominio_personalizado or self.subdominio_oficial

    @property
    def tiene_tema_personalizado(self):
        return bool(self.color_primario and self.color_primario.lower() != "#c89d3c")

    def __str__(self):
        return str(self.nombre)

class Alumno(models.Model):
    """ 
    Modelo que representa un Alumno
    """
    objects = models.Manager()

    usuario = models.OneToOneField(Usuario, on_delete=models.SET_NULL, verbose_name="Alumno", blank=True, null=True)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE, verbose_name="Dojo")
    instructor = models.BooleanField(default=False)
    grado = models.IntegerField(blank=True, null=True)
    RANGO_GRADO = (
        ('h', 'Hanshi'),
        ('r', 'Renshi'),
        ('k', 'Kyoshi'),
    )
    rango = models.CharField(max_length=1, choices=RANGO_GRADO, blank=True, null=True)
    fecha_rango = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)
    foto = models.ImageField(
        upload_to='administracion/fotos/%Y/%m', blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['apellidos', 'nombre']
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

    def __str__(self):
        return f'{self.apellidos}, {self.nombre}. {self.grado}'
    

class CargoDirectivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Cargo")
    orden_jerarquico = models.IntegerField(
        default=10, 
        help_text="Número menor para cargos superiores (ej. Presidente=1, Vicepresidente=2)"
    )
    class Meta:
        verbose_name = "Configuración de Cargo"
        verbose_name_plural = "Configuración de Cargos"
        ordering = ['orden_jerarquico']

    def __str__(self):
        return self.nombre

class MiembroDirectiva(models.Model):
        """
        Modelo para gestionar la Junta Directiva.
        Permite vincular a un Alumno existente O crear un perfil para externos (ej. Presidente).
        """
        objects = models.Manager()

        # Relación directa con Usuario (para el Presidente externo, por ejemplo)
        usuario = models.OneToOneField(
            Usuario, 
            on_delete=models.SET_NULL, 
            verbose_name="Cuenta de Usuario", 
            blank=True, 
            null=True,
            related_name="perfil_directivo" # Nombre único para evitar conflictos
        )

        # Relación opcional con Alumno
        alumno = models.ForeignKey(
            Alumno,
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            verbose_name="Alumno vinculado",
            help_text="Si el directivo es alumno, selecciónalo aquí. Si no, déjalo vacío y rellena los datos externos."
        )

        # Campos para externos (Solo se usan si alumno es None)
        nombre_externo = models.CharField(max_length=50, blank=True, verbose_name="Nombre (Externo)")
        apellidos_externo = models.CharField(max_length=50, blank=True, verbose_name="Apellidos (Externo)")
        foto_externa = models.ImageField(
            upload_to='directiva', blank=True, null=True, verbose_name="Foto (Externa)",
            validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
        )

        # Datos del cargo
        cargo = models.ForeignKey(CargoDirectivo, on_delete=models.PROTECT, verbose_name="Cargo directivo")
        orden = models.IntegerField(default=0, help_text="Para ordenar en la web (ej: Presidente=1, Vice=2...)")
        activo = models.BooleanField(default=True)

        class Meta:
            verbose_name = "Miembro de Directiva"
            verbose_name_plural = "Miembros de Directiva"
            ordering = ['orden']

        def clean(self):
            """Validación para asegurar consistencia"""
            if not self.alumno and not (self.nombre_externo and self.apellidos_externo):
                raise ValidationError("Debes vincular un Alumno O rellenar Nombre y Apellidos externos.")

        def save(self, *args, **kwargs):
            self.full_clean() # Ejecuta la validación antes de guardar
            super().save(*args, **kwargs)

        # Propiedades dinámicas para facilitar el uso en Templates (Bootstrap)

        def es_practicante(self):
            """
            Retorna True si el directivo es un alumno.
            No necesita importar el modelo Alumno porque ya tiene el campo ForeignKey.
            """
            return self.alumno is not None

        @property
        def obtener_nombre_mostrable(self):
            if self.es_practicante():
                return f"{self.alumno.nombre} {self.alumno.apellidos}"
            # Si no es alumno, usamos el nombre externo que definimos antes
            return f"{self.nombre_externo} {self.apellidos_externo}"

        @property
        def get_foto_url(self):
            if self.alumno and self.alumno.foto:
                return self.alumno.foto.url
            if self.foto_externa:
                return self.foto_externa.url
            # Puedes añadir lógica aquí para sacar la foto del modelo Usuario si tuviera
            return "/static/img/foto.png"

        def __str__(self):
            return f"{self.cargo}: {self.obtener_nombre_mostrable}"

class Cursillo(models.Model):
    """
    Listado de los cursillos
    """
    objects = models.Manager()

    evento = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    lugar = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=50)
    internacional = models.BooleanField(default=False, blank=True, null=True)
    pais = models.CharField(max_length=50, default='España')
    fecha = models.DateField(auto_now=False, auto_now_add=False)
    examenes = models.BooleanField(default=False, blank=True, null=True)
    alumnos = models.ManyToManyField(Alumno, blank=True)
    circular = models.FileField(
        upload_to='pdf', max_length=100, blank=True, null=True, default=None,
        validators=[FileExtensionValidator(['pdf'])]
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.fecha} - {self.evento}'

class Examen(models.Model):
    """
    Realización de exámenes
    """
    objects = models.Manager()

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    evento = models.ForeignKey(Cursillo, on_delete=models.CASCADE)
    grado = models.IntegerField()

    class Meta:
        verbose_name_plural = "Examenes"
        ordering = ['grado']

    def __str__(self):
        return f'{self.alumno} - {self.grado}'

class Peticion(models.Model):
    """Petición realizada por un instructor"""
    objects = DojoScopedManager()

    fecha = models.DateField(auto_now=False, auto_now_add=True)
    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    TIPO_PETICION = (
        ('a', 'Añadir'),
        ('m', 'Modificar'),
        ('e', 'Eliminar'),
    )
    titulo = models.CharField(max_length=550)
    tipo = models.CharField(max_length=1, choices=TIPO_PETICION, blank=True, null=True)
    descripcion = models.TextField()
    finalizada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Peticion"
        verbose_name_plural = "Peticiones"
        ordering = ['-fecha', 'dojo']

    def __str__(self):
        return f'{self.fecha}: {self.titulo} - {self.finalizada}'

class Tablon(models.Model):
    """
    Tablón de anuncions para cada Dojo
    """
    objects = DojoScopedManager()

    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=250)
    descripcion = models.TextField()
    fecha = models.DateField(auto_now=False, auto_now_add=False)
    lugar = models.CharField(max_length=100, blank=True, null=True)
    informacion = models.FileField(
        upload_to='pdf', max_length=100, blank=True, null=True, default=None,
        validators=[FileExtensionValidator(['pdf'])]
    )

    class Meta:
        verbose_name = "Tablon"
        verbose_name_plural = "Tablones"
        ordering = ['fecha']

    def __str__(self):
        return f'{self.fecha}: {self.titulo}'

class Actividad(models.Model):
    """
    Actividades de la asociación OGKKE
    """
    
    objects = models.Manager()

    tipo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=250)
    descripcion = models.TextField()
    fecha = models.DateField(auto_now=False, auto_now_add=False)
    lugar = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=50, blank=True, null=True)
    provincia = models.CharField(max_length=50, blank=True, null=True)
    pais = models.CharField(max_length=50, default='España')

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ['fecha']

    def __str__(self): 
        return f'{self.fecha}: {self.titulo}'

class Proverbio(models.Model):
    """
        Proverbios de la filosofía japonesa
    """
    objects = models.Manager()

    texto = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Proverbio"
        verbose_name_plural = "Proverbios"
        ordering = ['texto']

    def __str__(self):
        return f'{self.texto}'


class GradoKyu(models.Model):
    """
    Catálogo jerárquico de Cinturones de Color (grados Kyu, inferiores a Cinturón Negro).
    Incluye grados base adultos/general y grados bicolores intermedios infantiles.
    """
    objects = models.Manager()

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Cinturón")
    kyu_referencia = models.CharField(
        max_length=25,
        blank=True,
        default="",
        verbose_name="Referencia Kyu",
        help_text="Ej. 10º Kyu, 9º Kyu, 3º-1º Kyu..."
    )
    orden = models.PositiveSmallIntegerField(
        unique=True,
        db_index=True,
        verbose_name="Nivel / Orden jerárquico",
        help_text="Valor numérico ascendente (ej. Blanco=10 ... Marrón=110) para filtros y ascensos."
    )
    es_intermedio_infantil = models.BooleanField(
        default=False,
        verbose_name="Grado intermedio infantil",
        help_text="Indica si es un cinturón bicolor intermedio para categorías infantiles."
    )
    color_hex_primario = models.CharField(
        max_length=7,
        default="#ffffff",
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name="Color principal (Hex)"
    )
    color_hex_secundario = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name="Color secundario (Hex, bicolores)"
    )

    class Meta:
        verbose_name = "Grado Kyu (Cinturón de Color)"
        verbose_name_plural = "Grados Kyu (Cinturones de Color)"
        ordering = ['orden']

    @property
    def es_bicolor(self):
        return bool(self.color_hex_secundario)

    def __str__(self):
        return f"{self.nombre} ({self.kyu_referencia})" if self.kyu_referencia else self.nombre


class AlumnoColorQuerySet(DojoScopedQuerySet):
    """
    QuerySet con aislamiento estricto por rol/Dojo (RGPD / LOPDGDD):
    - Staff/Superuser de la asociación: acceso completo.
    - Instructor titular activo: exclusivamente alumnos de su propio Dojo.
    - Resto de usuarios (cintos negros regulares, jueces efímeros, anónimos): .none()
    """

    def for_user(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_staff or user.is_superuser:
            return self.all()
        instructor_dojo_ids = list(
            Alumno.objects.filter(
                usuario=user,
                instructor=True,
                activo=True,
            ).values_list('dojo_id', flat=True)
        )
        if instructor_dojo_ids:
            return self.filter(dojo_id__in=instructor_dojo_ids)
        return self.none()


AlumnoColorManager = models.Manager.from_queryset(AlumnoColorQuerySet)


class AlumnoColor(models.Model):
    """
    Modelo para practicantes de Cinturón de Color (Kyu) y Menores.
    Cumple estrictamente el principio de minimización de datos (RGPD Art. 5.1.c)
    y el control de consentimiento paterno para menores de 14 años (LOPDGDD Art. 7).
    """
    objects = AlumnoColorManager()

    GENERO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('X', 'No especificado'),
    )

    codigo_interno = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Identificador opaco (Anti-IDOR)"
    )
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    apellidos = models.CharField(max_length=80, db_index=True, verbose_name="Apellidos")
    fecha_nacimiento = models.DateField(
        db_index=True,
        verbose_name="Fecha de nacimiento",
        help_text="Obligatoria para el cálculo exacto de edad y control de mayoría legal."
    )
    genero = models.CharField(
        max_length=1,
        choices=GENERO_CHOICES,
        default='X',
        verbose_name="Género"
    )
    dojo = models.ForeignKey(
        Dojo,
        on_delete=models.CASCADE,
        related_name="alumnos_color",
        verbose_name="Dojo"
    )
    grado_actual = models.ForeignKey(
        GradoKyu,
        on_delete=models.PROTECT,
        related_name="alumnos",
        verbose_name="Cinturón actual"
    )
    fecha_ultimo_grado = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha obtención grado actual"
    )

    # Control explícito de protección de datos y autorización paterna/tutorial (RGPD / LOPDGDD)
    consentimiento_firmado = models.BooleanField(
        default=False,
        verbose_name="Autorización RGPD / Paterna firmada",
        help_text="Obligatorio para activar la ficha o competir si el alumno es menor de 14 años."
    )
    consentimiento_campeonatos = models.BooleanField(
        default=False,
        verbose_name="Autorizado para participar en campeonatos",
        help_text="Autoriza el tratamiento y llamado en tatami durante torneos oficiales."
    )
    fecha_firma_consentimiento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de firma de autorización"
    )
    referencia_consentimiento = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Referencia / Código de archivo de la autorización",
        help_text="Ej. Expediente físico Dojo #2026-014 o referencia de documento firmado."
    )
    documento_consentimiento = models.FileField(
        upload_to='privado/consentimientos/%Y/%m',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name="Documento de autorización (PDF opcional)"
    )

    activo = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Alta activa"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alumno de Cinturón de Color"
        verbose_name_plural = "Alumnos de Cinturón de Color"
        ordering = ['apellidos', 'nombre']
        indexes = [
            models.Index(fields=['dojo', 'activo', 'grado_actual']),
            models.Index(fields=['dojo', 'apellidos', 'nombre']),
        ]

    def edad_en_fecha(self, fecha_ref=None):
        """Calcula la edad exacta del alumno en la fecha indicada (o hoy por defecto)."""
        return calcular_edad_en_fecha(self.fecha_nacimiento, fecha_ref)

    @property
    def edad(self):
        return self.edad_en_fecha()

    @property
    def es_menor_14(self):
        """En España (Art. 7 LOPDGDD), los menores de 14 años requieren consentimiento de padres/tutores."""
        return self.edad < 14

    @property
    def es_menor_edad(self):
        """Menor de 18 años."""
        return self.edad < 18

    @property
    def tiene_autorizacion_valida(self):
        """
        Verifica si el alumno cumple con los requisitos de autorización.
        Para menores de 14 años exige consentimiento_firmado=True y fecha_firma_consentimiento.
        """
        if self.es_menor_14:
            return bool(self.consentimiento_firmado and self.fecha_firma_consentimiento)
        return True

    @property
    def puede_competir(self):
        """
        Determina si el alumno está habilitado para ser inscrito en campeonatos.
        Si es menor de 18 años requiere consentimiento firmado y autorización de campeonatos;
        si es menor de 14 exige además fecha de firma validada.
        """
        if not self.activo:
            return False
        if self.es_menor_14:
            return bool(
                self.consentimiento_firmado
                and self.consentimiento_campeonatos
                and self.fecha_firma_consentimiento
            )
        if self.es_menor_edad:
            return bool(self.consentimiento_firmado and self.consentimiento_campeonatos)
        return True

    def clean(self):
        super().clean()
        hoy = datetime.date.today()
        if self.fecha_nacimiento and self.fecha_nacimiento > hoy:
            raise ValidationError({
                'fecha_nacimiento': "La fecha de nacimiento no puede ser futura."
            })

        if self.fecha_nacimiento:
            edad_actual = self.edad_en_fecha(hoy)
            if edad_actual < 14 and self.activo:
                if not self.consentimiento_firmado or not self.fecha_firma_consentimiento:
                    raise ValidationError(
                        "Normativa RGPD/LOPDGDD (Menores de 14 años): No se puede dar de alta activa "
                        "a un menor de 14 años sin la autorización paterna/tutorial firmada y su fecha de firma."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.apellidos}, {self.nombre} ({self.grado_actual.nombre})"


class HistorialGradoKyu(models.Model):
    """
    Registro histórico de ascensos de cinturón de color (Kyu) dentro del Dojo.
    """
    objects = models.Manager()

    alumno_color = models.ForeignKey(
        AlumnoColor,
        on_delete=models.CASCADE,
        related_name="historial_grados",
        verbose_name="Alumno"
    )
    grado = models.ForeignKey(
        GradoKyu,
        on_delete=models.PROTECT,
        verbose_name="Grado obtenido"
    )
    fecha_examen = models.DateField(
        default=datetime.date.today,
        verbose_name="Fecha de pase de grado"
    )
    evaluador = models.ForeignKey(
        Alumno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Instructor evaluador"
    )
    observaciones = models.CharField(
        max_length=250,
        blank=True,
        default="",
        verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Historial de Grado Kyu"
        verbose_name_plural = "Historial de Grados Kyu"
        ordering = ['-fecha_examen', '-grado__orden']

    def __str__(self):
        return f"{self.alumno_color} -> {self.grado.nombre} ({self.fecha_examen})"
