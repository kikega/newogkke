"""
Modelos de administración
"""
# Django
from django.db import models
from django.core.exceptions import ValidationError

# Importamos el modelo de Usuario
from usuarios.models import Usuario
class Dojo(models.Model):
    """
    Modelo que representa un gimnasio de la asociación
    """
    objects = models.Manager()

    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    direccion = models.CharField(max_length=100, verbose_name="Dirección")
    poblacion = models.CharField(max_length=100, verbose_name="Población")
    provincia = models.CharField(max_length=100, verbose_name="Provincia")
    codigo_postal = models.CharField(max_length=5, verbose_name="Código Postal")

    class Meta:
        verbose_name = "Dojo"
        verbose_name_plural = "Dojos"
        ordering = ['nombre']

    def __str__(self):
        return str(self.nombre)

class Alumno(models.Model):
    """ 
    Modelo que representa un Alumno
    """
    objects = models.Manager()

    username = None # No usamos el username
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
    foto = models.ImageField(upload_to='administracion', blank=True, null=True)
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
        foto_externa = models.ImageField(upload_to='directiva', blank=True, null=True, verbose_name="Foto (Externa)")

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
            return "/static/img/default-avatar.png"

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
    alumnos = models.ManyToManyField(Alumno, blank=True, null=True)
    circular = models.FileField(upload_to='pdf', max_length=100, blank=True, null=True, default=None)

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
    objects = models.Manager()

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
    objects = models.Manager()

    dojo = models.ForeignKey(Dojo, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=250)
    descripcion = models.TextField()
    fecha = models.DateField(auto_now=False, auto_now_add=False)
    lugar = models.CharField(max_length=100, blank=True, null=True)
    informacion = models.FileField(upload_to='pdf', max_length=100, blank=True, null=True, default=None)

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
