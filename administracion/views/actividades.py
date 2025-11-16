"""
Vistas relacionadas con la gestión de actividades
"""

# Python
import datetime

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.template.loader import render_to_string

# App administracion
from administracion.models import Actividad

# Formularios
from administracion.forms import ActividadNuevaForm, ActividadEditForm

# Utilidades
from administracion.utils import is_ajax

class ActividadesView(LoginRequiredMixin, TemplateView):
    """
    Gestión de actividades
    """

    template_name = "administracion/actividades.html"

    def get_context_data(self, **kwargs):
        """
        Obtenemos todas las actividades
        """

        context = super().get_context_data(**kwargs)

        # Obtenemos la fecha actual
        hoy = datetime.date.today()
        context["actividades"] = Actividad.objects.filter(fecha__gte=hoy).order_by('fecha')
        context['form'] = ActividadNuevaForm()

        return context

    def post(self, request, *args, **kwargs):
        """
        Procesa el formulario de nueva actividad
        """

        # Obtenemos los datos del formulario
        form = ActividadNuevaForm(request.POST)
        if form.is_valid():
            try:
                titulo = form.cleaned_data['titulo']
                descripcion = form.cleaned_data['descripcion']
                fecha = form.cleaned_data['fecha']
                lugar = form.cleaned_data['lugar']
                ciudad = form.cleaned_data['ciudad']
                provincia = form.cleaned_data['provincia']
                pais = form.cleaned_data['pais']

                # Creamos la nueva actividad
                Actividad.objects.create(
                    titulo = titulo,
                    descripcion = descripcion,
                    fecha = fecha,
                    lugar = lugar,
                    ciudad = ciudad,
                    provincia = provincia,
                    pais = pais,
                )
                messages.success(self.request, "¡Actividad creada exitosamente!")
            except Exception as e:
                messages.error(self.request, f"Ocurrió un error al crear la actividad: {e}")
        else:
            messages.error(self.request, f'Ocurrió un error al crear la actividad: {form.errors}')

        return redirect('administracion:actividades')


class ActividadEditarView(LoginRequiredMixin, UpdateView):
    """
    Editar una actividad
    """

    model = Actividad
    form_class = ActividadEditForm
    template_name = 'administracion/actividades.html'
    success_url = reverse_lazy("administracion:actividades")

    # Sobrescribimos el método GET
    def get(self, request, *args, **kwargs):
        # Si la petición es AJAX, no devolvemos la página completa.
        if is_ajax(request):
            # Obtenemos el objeto que se está editando (UpdateView lo hace por nosotros)
            self.object = self.get_object()
            form = self.get_form()
            context = {'form': form, 'actividad': self.object}
            
            # Renderizamos solo el formulario parcial y lo devolvemos en un JSON
            html_form = render_to_string(
                'administracion/modales/modal_actividad_edit_form.html',
                context,
                request=request
            )
            return JsonResponse({'html_form': html_form})
        else:
            # Si no es AJAX, dejamos que UpdateView haga su trabajo normal
            return super().get(request, *args, **kwargs)
        
    # Sobrescribimos el método que se llama cuando el formulario es válido
    def form_valid(self, form):
        # Guardamos el objeto
        print(f'DEBUG: Formulario válido, guardando objeto')
        self.object = form.save()
        
        if is_ajax(self.request):
            # Si es AJAX, devolvemos un JSON indicando que todo fue bien
            return JsonResponse({'success': True, 'message': 'Actividad actualizada correctamente.'})
        else:
            # Si no, hacemos la redirección normal
            return super().form_valid(form)
        
    # Sobrescribimos el método que se llama cuando el formulario tiene errores
    def form_invalid(self, form):
        print(f'DEBUG: Formulario inválido: {form.errors}')
        if is_ajax(self.request):
            # Si es AJAX, renderizamos de nuevo el formulario con los errores
            # y lo devolvemos en un JSON para que el cliente lo muestre.
            context = {'form': form, 'actividad': self.get_object()}
            html_form = render_to_string(
                'administracion/modales/modal_actividad_edit_form.html',
                context,
                request=self.request
            )
            return JsonResponse({'success': False, 'html_form': html_form}, status=400)
        else:
            # Si no, dejamos que se renderice la página con los errores del formulario
            return super().form_invalid(form)
    


class ActividadEliminarView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar una actividad
    """

    model = Actividad
    success_url = reverse_lazy('administracion:actividades')