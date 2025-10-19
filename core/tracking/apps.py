from django.apps import AppConfig


class TrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.tracking'
    label = 'core_tracking'
    verbose_name = 'Tracking'