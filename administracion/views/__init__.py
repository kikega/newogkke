from .home import home
from .alumnos import AlumnosView, AlumnoDetailView
from .dojos import DojosView, DojoDetailView
from .dojo_portal import DojoPortalView, DojoPortalConfigUpdateView, tls_domain_check
from .cursillos import (
    CursillosView, CursilloDetailView, CursoNuevoView,
    CursilloExaminaListView, CursilloEstadisticasView,
    CursilloInscripcionInstructorView, CursilloInscripcionAlumnoView,
    descargar_circular
)
from .peticiones import PeticionView, PeticionAnularView
from .actividades import ActividadesView, ActividadEditarView, ActividadEliminarView
from .tablon import TablonView, TablonEditarView, TablonEliminarView
from .directiva import DirectivaView
from .varios import enviar_correo_instructores, ErrorView