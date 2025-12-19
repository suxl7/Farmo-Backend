from django.apps import AppConfig
from django.db.models.signals import post_migrate


def disable_permissions(sender, **kwargs):
    pass


class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'
    
    def ready(self):
        from django.contrib.auth.management import create_permissions
        post_migrate.disconnect(create_permissions, dispatch_uid="django.contrib.auth.management.create_permissions")
