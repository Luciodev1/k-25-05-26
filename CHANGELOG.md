# Changelog

## [1.1.0] — 2026-05-27

### Adicionado
- CSP com nonce (removido `unsafe-inline` de script-src)
- Health check endpoint: `GET /health/`
- `SECURE_PROXY_SSL_HEADER` activo em produção
- `gunicorn` e `django-storages` como dependências
- Configuração S3-compatible para media files
- Pre-commit hooks (black, flake8, isort)
- CI/CD pipeline (GitHub Actions) com lint + test + coverage
- Factory Boy factories para testes
- Tests de coverage para accounts, audit, users, reports
- Rate limiting em endpoints críticos (bulk delete, hard deletes, exports)
- Flower para monitoramento Celery
- `assertNumQueries` em testes de views críticas

### Corrigido
- XSS em `tenant_detail.html` (username sem `|escapejs`)
- CSP `unsafe-inline` substituído por nonce em scripts
- Log rotation ajustado de 5MB para 10MB (conforme spec)
- Celery RESULT_EXPIRES configurado para 86400s
- Rate limit com cool-down de 30 min e reset no login

### Removido
- `reports/base.py` (vestigial)
- `reports/filters.py` (não utilizado)
- `tests/conftest.py` (duplicado)
- `cache_utils.py` (lógica inline nos signals)

## [1.0.0] — 2026-05-22

### Adicionado
- Release inicial do SGE
- Gestão de marcas, categorias, produtos
- Entradas e saídas de stock
- Entregas com soft delete atómico
- Contas a pagar/receber
- Relatórios com export Excel/PDF
- Autenticação com rate limiting
- Multi-tenant isolation
- Cache com invalidação automática
- Auditoria de operações
- Backup automático via Celery
- Config parser para JSON
- Suite de testes com 94% cobertura
