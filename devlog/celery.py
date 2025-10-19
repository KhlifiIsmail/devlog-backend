import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devlog.settings')

app = Celery('devlog')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Future AI tasks will go here
    # Example:
    # 'generate-weekly-insights': {
    #     'task': 'insights.tasks.generate_weekly_insights',
    #     'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
    # },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')