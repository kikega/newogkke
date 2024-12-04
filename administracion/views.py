""" Vistas de la app administracion """

# Django
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def home(request):
    """Home de la aplicación"""

    return render(request, 'administracion/home.html')
