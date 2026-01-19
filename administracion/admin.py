from django.contrib import admin
from django.utils.html import mark_safe

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

class CargoDirectivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden_jerarquico')
    ordering = ('orden_jerarquico',)
class MiembroDirectivaAdmin(admin.ModelAdmin):
        # Campos que se ven en la lista general
        list_display = ('foto_preview', 'cargo', 'get_nombre_completo', 'tipo_miembro', 'orden', 'activo')

        # Campos que puedes editar directamente sin entrar en la ficha (útil para reordenar rápido)
        list_editable = ('orden', 'activo')

        # Filtros laterales
        list_filter = ('cargo', 'activo')

        # Buscador (busca tanto en alumnos vinculados como en nombres externos)
        search_fields = ('alumno__nombre', 'alumno__apellidos', 'nombre_externo', 'apellidos_externo')

        # Habilita el buscador tipo AJAX para elegir el alumno (mucho mejor para 500 registros)
        autocomplete_fields = ['alumno']

        # Organización del formulario de edición
        fieldsets = (
            ('Información del Cargo', {
                'fields': ('cargo', 'orden', 'activo'),
                'description': 'Defina el puesto y la prioridad de visualización (1 aparece primero).'
            }),
            ('Opción A: Vincular Alumno Existente', {
                'fields': ('alumno',),
                'description': '<strong>Recomendado:</strong> Use esto si la persona ya es practicante. Se usará su foto y datos automáticamente.',
            }),
            ('Opción B: Datos para Externos', {
                'fields': ('nombre_externo', 'apellidos_externo', 'foto_externa'),
                'description': 'Rellene esto <strong>SOLO</strong> si la persona NO es alumno (ej. Presidente no practicante).',
                'classes': ('collapse',), # Esto hace que la sección salga plegada por defecto para no molestar
            }),
        )

        # --- Funciones auxiliares para mostrar datos en el Admin ---

        def get_nombre_completo(self, obj):
            """Muestra el nombre usando la lógica del modelo"""
            return obj.obtener_nombre_mostrable
        get_nombre_completo.short_description = "Nombre Completo"
        get_nombre_completo.admin_order_field = 'alumno__nombre' # Permite ordenar por nombre

        def tipo_miembro(self, obj):
            """Indica visualmente si es interno o externo"""
            if obj.alumno:
                return mark_safe('<span style="color: green;">✔ Practicante</span>')
            return mark_safe('<span style="color: orange;">★ Externo</span>')
        tipo_miembro.short_description = "Tipo"

        def foto_preview(self, obj):
            """Muestra una miniatura de la foto en el listado"""
            url = obj.get_foto_url # Usamos la propiedad que creamos en el modelo
            if url:
                return mark_safe(f'<img src="{url}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 50%;" />')
            return "-"
        foto_preview.short_description = "Foto"

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
#admin.site.register(MiembroDirectiva, MiembroDirectivaAdmin)
#admin.site.register(CargoDirectivo, CargoDirectivoAdmin)