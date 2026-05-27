# Relatório de Implementação — System Improvements and Hardening

Data: 2026-05-22

## Resumo

Implementadas as 29 tarefas do spec `.kiro/specs/system-improvements-and-hardening/tasks.md`, cobrindo infraestrutura, validação, concorrência, cache, segurança, relatórios, soft delete de entregas, testes e documentação.

## Componentes principais

| Área | Ficheiros |
|------|-----------|
| Infra | `app/settings.py`, `app/celery.py`, `app/tasks.py`, `.env.example` |
| Validadores | `app/validators.py` |
| Cache | `app/cache_utils.py`, signals em apps |
| Segurança | `users/views.CustomLoginView`, `app/static/js/csrf.js` |
| Stock/Entregas | `outflows/models.py` (Delivery soft delete atómico) |
| Relatórios | `reports/filters.py`, `reports/mixins.py`, `reports/tasks.py` |
| Config | `app/config_parser.py`, `config.example.json` |
| Testes | `tests/`, `pytest.ini` |

## Testes

- Suite completa: **87 testes** passam (`pytest --no-cov`)
- Inclui testes novos: validadores, cache, config parser, integração outflow/delivery

## Migrations

Aplicadas migrations para constraints, índices, campos `Delivery.is_deleted`, `Supplier.nif/email`, etc.

## Notas operacionais

- `django-filter` actualizado para >=24.3 (compatível Django 6)
- Login customizado com rate limit 5/15min por IP
- Backup Celery diário às 02:00 via `app.tasks.backup_database`
