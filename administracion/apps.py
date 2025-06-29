from django.apps import AppConfig


class AdministracionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administracion'

    def ready(self):
        """
        Se ejecuta cuando Django termina de cargar la aplicación
        """
        import administracion.signals
