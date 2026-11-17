"""URLs de la app campeonatos."""
from django.urls import path
from campeonatos import views

app_name = 'campeonatos'

urlpatterns = [
    path("", views.CampeonatosListView.as_view(), name="lista"),
    path("ayuda/", views.CampeonatosAyudaView.as_view(), name="ayuda"),
    path("nuevo/", views.CampeonatoCreateView.as_view(), name="nuevo"),
    path("historico/", views.CampeonatosHistoricoView.as_view(), name="historico"),
    path("torneo/<slug:slug>/", views.CampeonatoDetailView.as_view(), name="detalle"),
    path("torneo/<slug:slug>/tatami/nuevo/", views.TatamiCreateView.as_view(), name="tatami_nuevo"),
    path("torneo/<slug:slug>/categoria/nueva/", views.CategoriaCreateView.as_view(), name="categoria_nueva"),
    path("categoria/<int:pk>/", views.CategoriaDetailView.as_view(), name="categoria_detalle"),
    path("categoria/<int:categoria_id>/inscribir/", views.InscripcionCreateView.as_view(), name="inscribir"),
    path("inscripcion/<int:pk>/eliminar/", views.InscripcionDeleteView.as_view(), name="inscripcion_eliminar"),
    path("tatami/<int:tatami_id>/credenciales/", views.TatamiRegenerarCredencialesView.as_view(), name="tatami_regenerar_credenciales"),
    # Panel Operativo de Tatami en Vivo (accesible a jueces efímeros durante el evento)
    path("tatami/<int:tatami_id>/", views.TatamiLiveView.as_view(), name="tatami_live"),
    path("tatami/<int:tatami_id>/iniciar/<int:categoria_id>/", views.TatamiIniciarCategoriaView.as_view(), name="tatami_iniciar_categoria"),
    path("tatami/<int:tatami_id>/puntuar/<int:actuacion_id>/", views.TatamiRegistrarPuntuacionView.as_view(), name="tatami_puntuar"),
    path("tatami/<int:tatami_id>/combate/<int:combate_id>/", views.TatamiRegistrarCombateView.as_view(), name="tatami_combate"),
    path("tatami/<int:tatami_id>/cerrar-ronda/<int:ronda_id>/", views.TatamiCerrarRondaView.as_view(), name="tatami_cerrar_ronda"),
]
