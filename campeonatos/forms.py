"""
Formularios para la creación y gestión de Campeonatos, Tatamis, Categorías e Inscripciones.
"""
from django import forms

from administracion.models import Alumno, AlumnoColor, Dojo, GradoKyu
from administracion.permissions import obtener_dojo_instructor, usuario_es_staff_asociacion
from campeonatos.models import (
    Campeonato,
    CategoriaCampeonato,
    InscripcionCampeonato,
    Tatami,
)


class CampeonatoForm(forms.ModelForm):
    """
    Formulario para crear o editar un Campeonato.
    Los instructores locales solo pueden crear torneos de ámbito LOCAL para su propio Dojo;
    el Staff de OGKKE puede crear torneos GENERALES o LOCALES.
    """

    class Meta:
        model = Campeonato
        fields = [
            'nombre',
            'ambito',
            'dojo_organizador',
            'sistema_puntuacion_default',
            'fecha_inicio',
            'fecha_fin',
            'lugar',
            'ciudad',
            'estado',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'ambito': forms.Select(attrs={'class': 'form-select'}),
            'dojo_organizador': forms.Select(attrs={'class': 'form-select'}),
            'sistema_puntuacion_default': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'required': True},
                format='%Y-%m-%d',
            ),
            'fecha_fin': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'required': True},
                format='%Y-%m-%d',
            ),
            'lugar': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and not usuario_es_staff_asociacion(self.user):
            dojo_inst = obtener_dojo_instructor(self.user)
            self.fields['ambito'].choices = [('LOCAL', 'Local (Dojo único)')]
            self.fields['ambito'].initial = 'LOCAL'
            if dojo_inst:
                self.fields['dojo_organizador'].queryset = Dojo.objects.filter(pk=dojo_inst.pk)
                self.fields['dojo_organizador'].initial = dojo_inst
            else:
                self.fields['dojo_organizador'].queryset = Dojo.objects.none()


class TatamiForm(forms.ModelForm):
    """Formulario para dar de alta un Tatami y generar sus credenciales efímeras de mesa."""

    generar_credenciales = forms.BooleanField(
        required=False,
        initial=True,
        label="Generar usuario efímero de Juez / Mesa automáticamente",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Tatami
        fields = ['numero', 'nombre', 'num_jueces_mesa']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20, 'required': True}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Tatami 1 - Pista Central',
                'required': True,
            }),
            'num_jueces_mesa': forms.Select(
                choices=[(3, '3 Jueces'), (5, '5 Jueces')],
                attrs={'class': 'form-select'},
            ),
        }


class CategoriaCampeonatoForm(forms.ModelForm):
    """
    Formulario para configurar una Categoría de Campeonato (Kata o Kumite).
    Recuerda que Kumite exige edad_min >= 18 años.
    """

    class Meta:
        model = CategoriaCampeonato
        fields = [
            'nombre',
            'modalidad',
            'sistema',
            'tatami',
            'genero',
            'edad_min',
            'edad_max',
            'admite_cintos_color',
            'grado_kyu_min',
            'grado_kyu_max',
            'admite_cintos_negros',
            'grado_dan_min',
            'grado_dan_max',
            'clasificados_siguiente_ronda',
            'orden_ejecucion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Alevín Mixto Cintos de Color (8-9 años)',
                'required': True,
            }),
            'modalidad': forms.Select(attrs={'class': 'form-select'}),
            'sistema': forms.Select(attrs={'class': 'form-select'}),
            'tatami': forms.Select(attrs={'class': 'form-select'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'edad_min': forms.NumberInput(attrs={'class': 'form-control', 'min': 4, 'max': 99}),
            'edad_max': forms.NumberInput(attrs={'class': 'form-control', 'min': 4, 'max': 99}),
            'admite_cintos_color': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'grado_kyu_min': forms.Select(attrs={'class': 'form-select'}),
            'grado_kyu_max': forms.Select(attrs={'class': 'form-select'}),
            'admite_cintos_negros': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'grado_dan_min': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'grado_dan_max': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'clasificados_siguiente_ronda': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 16}),
            'orden_ejecucion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        campeonato = kwargs.pop('campeonato', None)
        super().__init__(*args, **kwargs)
        self.fields['grado_kyu_min'].queryset = GradoKyu.objects.all().order_by('orden')
        self.fields['grado_kyu_max'].queryset = GradoKyu.objects.all().order_by('orden')
        if campeonato:
            self.fields['tatami'].queryset = Tatami.objects.filter(campeonato=campeonato).order_by('numero')
        else:
            self.fields['tatami'].queryset = Tatami.objects.none()


class InscripcionCompetidorForm(forms.Form):
    """
    Formulario para inscribir un AlumnoColor o un Alumno (DAN) en una categoría,
    filtrando estrictamente por visibilidad RGPD del usuario y elegibilidad por fecha de cumpleaños.
    """

    alumno_color = forms.ModelChoiceField(
        queryset=AlumnoColor.objects.none(),
        required=False,
        label="Alumno de Cinturón de Color (Kyu)",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    alumno_dan = forms.ModelChoiceField(
        queryset=Alumno.objects.none(),
        required=False,
        label="Alumno de Cinturón Negro (DAN)",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.categoria = kwargs.pop('categoria', None)
        super().__init__(*args, **kwargs)

        if not self.user or not self.categoria:
            return

        campeonato = self.categoria.campeonato
        es_staff = usuario_es_staff_asociacion(self.user)
        dojo_inst = obtener_dojo_instructor(self.user)

        # 1. Cintos de Color visibles por el usuario (Aislamiento estricto por Dojo)
        if self.categoria.admite_cintos_color:
            qs_color = (
                AlumnoColor.objects.for_user(self.user)
                .filter(activo=True)
                .select_related('dojo', 'grado_actual')
            )
            if campeonato.ambito == 'LOCAL' and campeonato.dojo_organizador_id:
                qs_color = qs_color.filter(dojo_id=campeonato.dojo_organizador_id)

            ya_inscritos_color = InscripcionCampeonato.objects.filter(
                categoria=self.categoria,
                alumno_color__isnull=False,
            ).values_list('alumno_color_id', flat=True)
            qs_color = qs_color.exclude(id__in=ya_inscritos_color)

            self.fields['alumno_color'].queryset = qs_color
            self.fields['alumno_color'].label_from_instance = (
                lambda obj: (
                    f"[{obj.dojo.nombre}] {obj.apellidos}, {obj.nombre} · {obj.grado_actual.nombre} · "
                    f"{campeonato.calcular_edad_competidor(obj.fecha_nacimiento)} años en torneo"
                    + (" (SIN AUTORIZACIÓN RGPD)" if not obj.puede_competir else "")
                )
            )

        # 2. Cintos Negros
        if self.categoria.admite_cintos_negros:
            qs_dan = Alumno.objects.filter(activo=True, fecha_nacimiento__isnull=False).select_related('dojo')
            if not es_staff and dojo_inst:
                qs_dan = qs_dan.filter(dojo=dojo_inst)
            if campeonato.ambito == 'LOCAL' and campeonato.dojo_organizador_id:
                qs_dan = qs_dan.filter(dojo_id=campeonato.dojo_organizador_id)

            ya_inscritos_dan = InscripcionCampeonato.objects.filter(
                categoria=self.categoria,
                alumno_dan__isnull=False,
            ).values_list('alumno_dan_id', flat=True)
            qs_dan = qs_dan.exclude(id__in=ya_inscritos_dan)

            self.fields['alumno_dan'].queryset = qs_dan
            self.fields['alumno_dan'].label_from_instance = (
                lambda obj: (
                    f"[{obj.dojo.nombre}] {obj.apellidos}, {obj.nombre} · {obj.grado or 1}º DAN · "
                    f"{campeonato.calcular_edad_competidor(obj.fecha_nacimiento)} años en torneo"
                )
            )
