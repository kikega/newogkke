from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from usuarios.models import Usuario


class UsuarioUserAdmin(UserAdmin):
    """
    Administración del modelo de Usuario
    """
    model = Usuario
    list_display = ('email', 'username', 'externo', 'is_staff', 'is_active', 'last_login')
    list_filter = ('externo', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password','username', 'numero_telefono',)}),
        ('Permisos', {'fields': ('externo', 'is_staff', 'is_active', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'numero_telefono','password1', 'password2', 'externo', 'is_staff', 'is_active','groups','last_login')}
         ),
    )
    search_fields = ('email', 'username')
    ordering = ('email',)
    
# Register your models here.

admin.site.register(Usuario, UsuarioUserAdmin)
