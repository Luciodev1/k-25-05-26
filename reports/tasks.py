import io
import logging
from typing import Any
from celery import shared_task
from celery.app.task import Task
from django.apps import apps
from django.db.models import Model

logger = logging.getLogger(__name__)


def _get_field_value(obj: Model, field_name: str) -> str:
    value = obj
    for attr in field_name.split('.'):
        value = getattr(value, attr, '')
    return str(value) if value is not None else ''


def _model_fields(model) -> list[str]:
    skip = {'id', 'password', 'last_login', 'is_superuser',
            'is_staff', 'is_active', 'date_joined', 'user_permissions',
            'groups', 'polymorphic_ctype', 'tenant', 'deleted_at'}
    return [f.name for f in model._meta.get_fields()
            if hasattr(f, 'name') and f.name not in skip
            and not f.auto_created and not f.is_relation
            and not getattr(f, 'one_to_one', False) and not getattr(f, 'many_to_many', False)]


@shared_task(bind=True)
def generate_large_excel_export(
    self: Task,
    model_label: str,
    object_ids: list[int],
    filename: str,
    user_email: str | None = None,
) -> dict[str, Any]:
    from openpyxl import Workbook
    from django.core.files.storage import default_storage

    model = apps.get_model(model_label)
    fields = _model_fields(model)
    wb = Workbook()
    ws = wb.active
    headers = [model._meta.get_field(f).verbose_name.title() if model._meta.get_field(f).verbose_name else f for f in fields]
    ws.append(headers)

    for obj in model.objects.filter(pk__in=object_ids).iterator(chunk_size=500):
        ws.append([_get_field_value(obj, f) for f in fields])

    buffer = io.BytesIO()
    wb.save(buffer)
    path = f'exports/{self.request.id}_{filename}'
    buffer.seek(0)
    default_storage.save(path, buffer)
    logger.info('Export Excel concluído: %s (%d registos)', path, len(object_ids))

    _notify(user_email, f'Export Excel: {filename}', path)

    return {'status': 'ok', 'path': path, 'records': len(object_ids)}


@shared_task(bind=True)
def generate_large_pdf_export(
    self: Task,
    model_label: str,
    object_ids: list[int],
    filename: str,
    user_email: str | None = None,
) -> dict[str, Any]:
    from django.core.files.storage import default_storage
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    model = apps.get_model(model_label)
    fields = _model_fields(model)
    headers = [model._meta.get_field(f).verbose_name.title() if model._meta.get_field(f).verbose_name else f for f in fields]

    rows = []
    for obj in model.objects.filter(pk__in=object_ids).iterator(chunk_size=500):
        rows.append([_get_field_value(obj, f) for f in fields])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm)

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f'Export: {model._meta.verbose_name_plural.title()}', styles['Title']),
        Spacer(1, 0.5 * cm),
    ]

    available_width = landscape(A4)[0] - 3 * cm
    num_cols = len(headers)
    col_width = max(available_width / num_cols, 2 * cm)
    col_widths = [min(col_width, 6 * cm)] * num_cols

    table_data = [headers] + rows
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343A40')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]))
    elements.append(table)
    doc.build(elements)

    path = f'exports/{self.request.id}_{filename}'
    buffer.seek(0)
    default_storage.save(path, buffer)
    logger.info('Export PDF concluído: %s (%d registos)', path, len(object_ids))

    _notify(user_email, f'Export PDF: {filename}', path)

    return {'status': 'ok', 'path': path, 'records': len(object_ids)}


def _notify(user_email: str | None, task_name: str, path: str | None = None) -> None:
    if not user_email:
        return
    from app.tasks import notify_task_completion
    notify_task_completion.delay(user_email, task_name, path)
