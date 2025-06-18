from django.contrib import admin

# Modelos
from .models import *

class DojoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'poblacion', 'provincia', 'codigo_postal')
    search_fields = ('nombre',)

class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('apellidos','nombre','dojo','grado','instructor', 'activo')
    list_filter = ('dojo',)
    search_fields = ('nombre', 'apellidos')

class CursilloAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'evento', 'ciudad', 'pais', 'internacional')
    list_filter = ('ciudad', 'pais', 'internacional')
    date_hierarchy = 'fecha'
    filter_horizontal = ('alumnos',)


class ExamenAdmin(admin.ModelAdmin):
    list_display = ('evento', 'alumno', 'grado')
    raw_id_fields = ('alumno',)
    list_filter = ('evento',)


class PeticionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'dojo', 'titulo', 'finalizada')
    list_filter = ('dojo', 'finalizada')

class ActividadAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'titulo', 'lugar', 'ciudad', 'pais')
    list_filter = ('fecha', 'lugar', 'ciudad', 'pais')

class TablonAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'dojo', 'titulo')
    list_filter = ('dojo',)



admin.site.site_header = 'Panel de control OGKKE'
admin.site.index_title = 'Administración OGKKE'
admin.site.site_title = 'Admin OGKKE'

admin.site.register(Dojo, DojoAdmin)
admin.site.register(Alumno, AlumnoAdmin)
admin.site.register(Cursillo, CursilloAdmin)
admin.site.register(Examen, ExamenAdmin)
admin.site.register(Peticion, PeticionAdmin)
admin.site.register(Actividad, ActividadAdmin)
admin.site.register(Tablon, TablonAdmin)