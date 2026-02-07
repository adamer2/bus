import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LilSholex.settings')
celery_app = Celery('LilSholex')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()
celery_app.conf.beat_schedule = {
    'periodic_playlist_event_handler': {
        'task': 'persianmeme.tasks.periodic_playlist_event_handler',
        'options': {'queue': 'celery'},
        'schedule': crontab(minute='*/5')
    }
}
