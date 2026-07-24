from django.apps import AppConfig


class AdministracionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administracion'

    def ready(self):
        """
        Se ejecuta cuando Django termina de cargar la aplicación
        """
        import administracion.signals
        self._patch_template_context_copy()

    def _patch_template_context_copy(self):
        """
        Monkey-patch BaseContext.__copy__ para compatibilidad con Python 3.14+.

        Django 6.0 usa asignación dinámica de __class__ y __dict__ dentro de BaseContext.__copy__,
        lo que puede fallar en Python 3.14+ debido a optimizaciones del intérprete en el
        direccionamiento de atributos y dict-sharing, dejando a la copia resultante
        sin atributos críticos (como 'template' o 'request').
        """
        from django.template import context as context_module
        from copy import copy

        original_copy = context_module.BaseContext.__copy__

        def patched_copy(self_obj):
            duplicate = self_obj.__class__.__new__(self_obj.__class__)
            duplicate.__dict__ = copy(self_obj.__dict__)
            duplicate.dicts = self_obj.dicts[:]
            return duplicate

        if original_copy.__module__ != '__main__':
            context_module.BaseContext.__copy__ = patched_copy
