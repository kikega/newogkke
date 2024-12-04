"""Views de la app usuarios"""
from django.shortcuts import render, redirect

# Autenticacion
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def login_view(request):
    """Vista para hacer login en la aplicación"""
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, email=email, password=password)

        if user:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'usuarios/login.html', {'error': 'Usuario o password incorrecto'})

    return render(request, 'usuarios/login.html')


@login_required
def logout_view(request):
    """Vista para hacer logout en la aplicación"""
    logout(request)
    return redirect('login')
