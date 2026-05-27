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
    'export-excel-monthly': {
        'task': 'reports.tasks.generate_large_excel_export',
        'schedule': crontab(hour=3, minute=0, day_of_month='1'),
        'args': ('app.Outflow', [], 'relatorio_mensal.xlsx'),
    },
    'export-pdf-weekly': {
        'task': 'reports.tasks.generate_large_pdf_export',
        'schedule': crontab(hour=4, minute=0, day_of_week='mon'),
        'args': ('outflows.Outflow', [], 'relatorio_semanal.pdf'),
    },
}
