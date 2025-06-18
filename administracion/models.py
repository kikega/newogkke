"""
Modelos de administración
"""
# Django
from django.db import models

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
        ordering = ['dojo', 'fecha']

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
