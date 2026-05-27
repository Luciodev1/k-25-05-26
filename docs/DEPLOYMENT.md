# Guia de Deployment — SGE

## Pré-requisitos

- Python 3.12+
- Redis (cache, Celery, rate limiting)
- Variáveis de ambiente (ver `.env.example`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env com DJANGO_SECRET_KEY, REDIS_URL, etc.
python manage.py migrate
python manage.py collectstatic --noinput
```

## Celery

```bash
# Worker
celery -A app worker -l info

# Beat (backup diário às 02:00)
celery -A app beat -l info
```

## Checklist pré-deployment

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` único em produção
- [ ] `DJANGO_ALLOWED_HOSTS` configurado
- [ ] `REDIS_URL` e Celery operacionais
- [ ] `SENTRY_DSN` configurado (opcional)
- [ ] `BACKUP_DIR` com permissões de escrita
- [ ] Migrations aplicadas
- [ ] Testes: `pytest`

## Checklist pós-deployment

- [ ] Login e rate limiting funcionam
- [ ] Dashboard carrega com cache Redis
- [ ] Backup manual: `python manage.py backup_db`
- [ ] Verificar logs em `logs/django.log`
- [ ] Sentry recebe erros de teste

## Rollback

1. Parar workers Celery e Gunicorn/uWSGI
2. Restaurar base de dados: `cp backups/db_backup_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3`
3. Reverter código: `git checkout <tag-anterior>`
4. `python manage.py migrate` se necessário
5. Reiniciar serviços
