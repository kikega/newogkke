"""
Vistas relacionadas con la gestión de entradas en el Tablón de anuncios de cada dojo
"""

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.template.loader import render_to_string

# App administracion
from administracion.models import Alumno, Cursillo, Dojo, Tablon

# Formularios
from administracion.forms import TablonNuevoForm, TablonEditForm

# Utilidades
from administracion.utils import enviar_correo_html, validar_cadena, is_ajax

class TablonView(LoginRequiredMixin, TemplateView):
    """
    Creación de información en el tablón de anuncios de cada dojo
    """
    template_name = 'administracion/home-tablon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtenemos los datos del usuario logado
        user = self.request.user

        # Obtenemos los datos de cantidad de dojos, alumnos y seminarios
        cn = Alumno.objects.all().count()
        cursos = Cursillo.objects.all().count()
        dojos = Dojo.objects.all().count()

        # Obtenemos el dojo del usuario logado
        alumno = Alumno.objects.select_related('dojo').get(usuario=user)
        dojo = alumno.dojo

        context["dojo_usuario"] = dojo
        context["tablon"] = Tablon.objects.filter(dojo_id = dojo)
        context['cn'] = cn
        context['cursos'] = cursos
        context['dojos'] = dojos

        return context

    def post(self, request, **kwargs):
        """
        Procesa el formulario para la creación de una notificación el el Tablon de un dojo
        """

        # Obtenemos los datos del formulario
        form = TablonNuevoForm(request.POST)

        if form.is_valid():
            print(f'DEBUG: Formulario valido')
            try:
                dojo_id = request.POST.get('dojo')
                fecha = form.cleaned_data['fecha']
                tipo = form.cleaned_data['tipo']
                titulo = form.cleaned_data['titulo']
                descripcion = form.cleaned_data['descripcion']
                lugar = form.cleaned_data['lugar']
                if request.FILES.get('informacion'):
                    informacion = request.FILES["informacion"]
                else:
                    informacion = None

                # Obtener el Dojo
                dojo = get_object_or_404(Dojo, pk=dojo_id)

                # Creamos la nueva notificación
                Tablon.objects.create(
                    dojo = dojo,
                    fecha = fecha,
                    tipo = tipo,
                    titulo = titulo,
                    descripcion = descripcion,
                    lugar = lugar,
                    informacion = informacion
                )

                messages.success(self.request, "¡Notificación creada exitosamente!")
            except Exception as e:
                messages.error(self.request, f"Ocurrió un error al crear la notificación: {e}")
                print(e)
        else:
            messages.error(self.request, f'Ocurrió un error al crear la notificación: {form.errors}')

        return redirect('administracion:tablon')


class TablonEditarView(LoginRequiredMixin, UpdateView):
    """
        Editamos el contenido de una entrada en el Tablón de anuncios de l dojo
    """

    model = Tablon
    form_class = TablonEditForm
    template_name = 'administracion/home-tablon.html'
    success_url = reverse_lazy("administracion:tablon")

    # Sobrescribimos el método GET
    def get(self, request, *args, **kwargs):
        # Si la petición es AJAX, no devolvemos la página completa.
        if is_ajax(request):
            # Obtenemos el objeto que se está editando (UpdateView lo hace por nosotros)
            self.object = self.get_object()
            form = self.get_form()
            context = {'form': form, 'tablon': self.object}
            
            # Renderizamos solo el formulario parcial y lo devolvemos en un JSON
            html_form = render_to_string(
                'administracion/modales/modal_tablon_edit_form.html',
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
            return JsonResponse({'success': True, 'message': 'Anuncio actualizado correctamente.'})
        else:
            # Si no, hacemos la redirección normal
            return super().form_valid(form)
        
    # Sobrescribimos el método que se llama cuando el formulario tiene errores
    def form_invalid(self, form):
        print(f'DEBUG: Formulario inválido: {form.errors}')
        if is_ajax(self.request):
            # Si es AJAX, renderizamos de nuevo el formulario con los errores
            # y lo devolvemos en un JSON para que el cliente lo muestre.
            context = {'form': form, 'tablon': self.get_object()}
            html_form = render_to_string(
                'administracion/modales/modal_tablon_edit_form.html',
                context,
                request=self.request
            )
            return JsonResponse({'success': False, 'html_form': html_form}, status=400)
        else:
            # Si no, dejamos que se renderice la página con los errores del formulario
            return super().form_invalid(form)

 
class TablonEliminarView(LoginRequiredMixin, DeleteView):
    """
    Eliminación de un tablón de anuncios
    """
    model = Tablon
    # URL a la que se redirigirá después de una eliminación exitosa.
    # Usamos reverse_lazy para que la URL se resuelva cuando sea necesario.
    success_url = reverse_lazy('administracion:tablon')
 