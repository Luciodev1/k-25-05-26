FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=app.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/backups /app/staticfiles /app/media

EXPOSE 8000

FROM base AS dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]

FROM base AS worker
CMD ["celery", "-A", "app", "worker", "-l", "info"]

FROM base AS beat
CMD ["celery", "-A", "app", "beat", "-l", "info"]
