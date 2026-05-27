import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('sge')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'backup-database-daily': {
        'task': 'app.tasks.backup_database',
        'schedule': crontab(hour=2, minute=0),
    },
}
