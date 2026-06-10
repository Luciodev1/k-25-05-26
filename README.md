# K — Gestão de Stocks e Contas (SGE)

Sistema Django para gestão de inventário, saídas, entregas, contas de clientes/fornecedores e relatórios.

## Setup rápido

```bash
pip install -r requirements.txt
cp .env.example .env
# Definir DJANGO_SECRET_KEY e REDIS_PASSWORD em .env
python manage.py migrate
python manage.py runserver
```

## Variáveis de ambiente

Ver `.env.example` para `DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, `REDIS_URL`, `SENTRY_DSN`, `CELERY_*`, `BACKUP_DIR`, `APP_VERSION`.

### Gerar senha segura para Redis

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o output para `REDIS_PASSWORD` no `.env`. Esta senha é usada para autenticação no Redis (cache, Celery broker, WebSockets).

## Testes

```bash
pytest
```

## Celery e backup

```bash
celery -A app worker -l info
celery -A app beat -l info
```

Documentação completa: `docs/DEPLOYMENT.md` e `docs/IMPLEMENTATION_REPORT.md`.
