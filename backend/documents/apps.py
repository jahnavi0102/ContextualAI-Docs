# backend/documents/apps.py
from django.apps import AppConfig

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'

    def ready(self):
        # Import signals here so they are connected when the app is ready
        import documents.signals