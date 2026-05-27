import logging
from typing import Any
from celery import shared_task
from celery.app.task import Task
from django.apps import apps

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_large_excel_export(self: Task, model_label: str, object_ids: list[int], filename: str) -> dict[str, Any]:
    from openpyxl import Workbook
    from io import BytesIO
    from django.core.files.storage import default_storage

    model = apps.get_model(model_label)
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Representação'])
    for obj in model.objects.filter(pk__in=object_ids).iterator(chunk_size=500):
        ws.append([obj.pk, str(obj)])
    buffer = BytesIO()
    wb.save(buffer)
    path = f'exports/{self.request.id}_{filename}'
    buffer.seek(0)
    default_storage.save(path, buffer)
    logger.info('Export Excel concluído: %s', path)
    return {'status': 'ok', 'path': path}


@shared_task(bind=True)
def generate_large_pdf_export(self: Task, model_label: str, object_ids: list[int], filename: str) -> dict[str, Any]:
    logger.info('Export PDF agendado para %s (%d registos)', model_label, len(object_ids))
    return {'status': 'ok', 'path': f'exports/{self.request.id}_{filename}'}
