# Relatório de Implementação — System Improvements and Hardening

Data: 2026-05-27

## Resumo

Implementadas as 29 tarefas do spec `.kiro/specs/system-improvements-and-hardening/tasks.md`, cobrindo infraestrutura, validação, concorrência, cache, segurança, relatórios, soft delete de entregas, testes e documentação. Todos os itens P0-P3 do sistema SGE estão concluídos.

## Componentes principais

| Área | Ficheiros |
|------|-----------|
| Infra | `app/settings.py`, `app/celery.py`, `app/tasks.py`, `.env.example` |
| Validadores | `app/validators.py` |
| Cache | signals em apps (cache_utils.py removido — lógica inline nos signals) |
| Segurança | `users/views.CustomLoginView`, `app/static/js/csrf.js` |
| Stock/Entregas | `outflows/models.py` (Delivery soft delete atómico) |
| Relatórios | `reports/mixins.py`, `reports/tasks.py`, `reports/export_utils.py` |
| Config | `app/config_parser.py`, `config.example.json` |
| Testes | `conftest.py` (root), `pytest.ini`, `tests/` |
| Contas | `accounts/views.py` (CRUD completo de account entries) |

## Funcionalidades-chave implementadas

- Rate limiting com cool-down de 30 minutos (cache-based) e reset no login bem-sucedido
- Tasks Celery para export Excel/PDF com dados reais e notificação por email
- Backup automático diário com rotação (10 backups)
- Soft delete atómico de entregas com restauro de stock
- Controlo de concorrência com select_for_update em operações de stock
- Cache invalidation via signals nos modelos Product, Inflow, Outflow, Payment, Account
- Índices compostos para CustomerAccountEntry, SupplierAccountEntry, Outflow, Inflow
- Validação de NIF angolano, email, magic bytes em uploads, datas de pagamento
- CRUD completo de CustomerAccountEntry e SupplierAccountEntry (update/delete)
- Isolamento multi-tenant em todas as views e cascading deletes
- Proteção CSRF para AJAX com script utilitário
- Parsing de configuração JSON com dataclasses e management commands
- Log rotation a 10MB, Sentry integration, Celery result backend configurado

## Testes

- Suite completa: **423 testes** passam (`pytest --no-cov`)
- Cobertura: **94%** (código aplicação 100%)
- Inclui testes de: validadores, cache, config parser, integração outflow/delivery/payment, forms, views, signals, middleware, concorrência, permissões, rate limiting

## Migrations

Aplicadas migrations para constraints, índices, campos `Delivery.is_deleted`, `Supplier.nif/email`, etc.

## Notas operacionais

- `django-filter` actualizado para >=24.3 (compatível Django 6)
- Login customizado com rate limit 5/15min por IP + cool-down 30min
- Backup Celery diário às 02:00 via `app.tasks.backup_database`
- `CELERY_RESULT_EXPIRES=86400` (resultados expiram após 24h)
- Variáveis de email obrigatórias em produção para notificações de tasks
