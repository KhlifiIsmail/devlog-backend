"""
Django app configuration for AI services.
"""

from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.ai'
    label = 'core_ai'
    verbose_name = 'AI Services'

    def ready(self):
        """Initialize AI services when Django starts."""
        # Import any signals or startup code here if needed
        pass