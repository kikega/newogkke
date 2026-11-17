"""Configuración del panel de administración para campeonatos."""
from django.contrib import admin
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


@admin.register(Campeonato)
class CampeonatoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ambito', 'dojo_organizador', 'fecha_inicio', 'fecha_fin', 'ciudad', 'estado')
    list_filter = ('ambito', 'estado', 'fecha_inicio')
    search_fields = ('nombre', 'ciudad', 'lugar')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Tatami)
class TatamiAdmin(admin.ModelAdmin):
    list_display = ('campeonato', 'numero', 'nombre', 'juez_operador', 'num_jueces_mesa')
    list_filter = ('campeonato',)


@admin.register(CategoriaCampeonato)
class CategoriaCampeonatoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'campeonato', 'modalidad', 'sistema', 'edad_min', 'edad_max', 'tatami', 'estado')
    list_filter = ('modalidad', 'sistema', 'estado', 'campeonato')
    search_fields = ('nombre',)


@admin.register(InscripcionCampeonato)
class InscripcionCampeonatoAdmin(admin.ModelAdmin):
    list_display = ('dorsal', 'categoria', 'alumno_color', 'alumno_dan', 'descalificado')
    list_filter = ('categoria__campeonato', 'descalificado')


@admin.register(RondaCategoria)
class RondaCategoriaAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'numero', 'nombre', 'es_final', 'es_desempate', 'cerrada')
    list_filter = ('es_final', 'es_desempate', 'cerrada')


@admin.register(ActuacionPuntuacion)
class ActuacionPuntuacionAdmin(admin.ModelAdmin):
    list_display = ('ronda', 'inscripcion', 'nota_total', 'nota_media', 'evaluado', 'clasificado')


@admin.register(EnfrentamientoBanderas)
class EnfrentamientoBanderasAdmin(admin.ModelAdmin):
    list_display = ('ronda', 'orden_combate', 'aka_inscripcion', 'ao_inscripcion', 'ganador', 'finalizado')


@admin.register(ResultadoHistorico)
class ResultadoHistoricoAdmin(admin.ModelAdmin):
    list_display = ('campeonato', 'categoria', 'puesto', 'nombre_competidor_snapshot', 'dojo_nombre_snapshot', 'puntuacion_final_snapshot')
    list_filter = ('campeonato', 'puesto', 'modalidad_snapshot')
    readonly_fields = ('fecha_registro',)
