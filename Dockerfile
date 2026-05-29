FROM python:3.14-slim AS build

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=app.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

RUN mkdir -p /app/logs /app/backups /app/staticfiles /app/media

EXPOSE 8000

FROM build AS dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM build AS prod
RUN addgroup --system django && adduser --system --ingroup django django
RUN chown -R django:django /app/logs /app/backups /app/staticfiles /app/media
USER django
RUN python manage.py collectstatic --noinput
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python manage.py health_check || exit 1
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--graceful-timeout", "30", "--max-requests", "1000", "--max-requests-jitter", "100", "--access-logfile", "-", "--access-logformat", "%({X-Forwarded-For}i)s %l %u %t \"%r\" %s %b \"%{Referer}i\" \"%{User-Agent}i\"", "--error-logfile", "-"]

FROM build AS worker
USER django
CMD ["celery", "-A", "app", "worker", "-l", "info", "--concurrency=2", "--max-tasks-per-child=1000"]

FROM build AS beat
USER django
CMD ["celery", "-A", "app", "beat", "-l", "info"]
