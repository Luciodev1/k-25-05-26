import csv
import logging
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)
LARGE_EXPORT_THRESHOLD = 1000


class ReportExportMixin:
    """Exportação com streaming; delega para Celery se > 1000 registos."""

    export_headers = []
    export_fields = []

    def export_csv_streaming(self, queryset, filename='export.csv'):
        count = queryset.count()
        if count > LARGE_EXPORT_THRESHOLD:
            return self._delegate_async_export(queryset, 'csv', filename)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(self.export_headers)
        for obj in queryset.iterator(chunk_size=500):
            writer.writerow(self._row_for_object(obj))
        return response

    def _row_for_object(self, obj):
        row = []
        for field in self.export_fields:
            value = obj
            for attr in field.split('.'):
                value = getattr(value, attr, '')
            row.append(str(value) if value is not None else '')
        return row

    def _delegate_async_export(self, queryset, fmt, filename):
        from reports.tasks import generate_large_excel_export, generate_large_pdf_export
        ids = list(queryset.values_list('pk', flat=True)[:50000])
        model_label = queryset.model._meta.label
        user_email = getattr(getattr(self, 'request', None), 'user', None)
        email = user_email.email if user_email and user_email.is_authenticated else None
        if fmt == 'csv':
            task = generate_large_excel_export.delay(model_label, ids, filename, email)
        else:
            task = generate_large_pdf_export.delay(model_label, ids, filename, email)
        return JsonResponse({'task_id': task.id, 'status': 'pending'})
