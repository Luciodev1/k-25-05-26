# Guia de Deployment — SGE

## Pré-requisitos

- Python 3.13+
- PostgreSQL 16+ (recomendado; SQLite apenas para desenvolvimento)
- Redis (cache, Celery, rate limiting)
- Variáveis de ambiente (ver `.env.example`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env com DJANGO_SECRET_KEY, DATABASE_URL, REDIS_URL, etc.
python manage.py migrate
python manage.py collectstatic --noinput
```

## Servir com Gunicorn

```bash
gunicorn app.wsgi:application --workers 4 --bind 0.0.0.0:8000
```

## Celery

```bash
# Worker
celery -A app worker -l info

# Beat (backup diário às 02:00)
celery -A app beat -l info
```

## Health check

```bash
curl http://localhost:8000/health/
# Resposta: {"status": "healthy", "database": true, "cache": true, "version": "1.0.0"}
```

## Storage (S3)

Opcional. Definir `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`
no `.env` para usar S3-compatible. Caso contrário, usa armazenamento local.

## Checklist pré-deployment

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` único em produção
- [ ] `DJANGO_ALLOWED_HOSTS` configurado
- [ ] PostgreSQL configurado (não SQLite)
- [ ] `REDIS_URL` e Celery operacionais
- [ ] `SECURE_PROXY_SSL_HEADER` activo (nginx/configurado)
- [ ] `SENTRY_DSN` configurado (opcional)
- [ ] `BACKUP_DIR` com permissões de escrita
- [ ] Migrations aplicadas
- [ ] Testes: `pytest`

## Checklist pós-deployment

- [ ] Health check: `curl /health/` retorna `healthy`
- [ ] Login e rate limiting funcionam
- [ ] Dashboard carrega com cache Redis
- [ ] Backup manual: `python manage.py backup_db`
- [ ] Verificar logs em `logs/django.log`
- [ ] Sentry recebe erros de teste
- [ ] CSP nonce funcional (inspeccionar headers HTTP)

## Rollback

1. Parar workers Celery e Gunicorn
2. Restaurar base de dados: `psql sge < backup.sql` ou `cp backups/db_backup_*.sqlite3 db.sqlite3`
3. Reverter código: `git checkout <tag-anterior>`
4. `python manage.py migrate` se necessário
5. Reiniciar serviços
