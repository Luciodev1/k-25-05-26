# Tasks

## Task 1: Configurar Infraestrutura Base (Redis, Celery, Sentry)
**Requirement IDs**: 5, 12, 13, 25
**Description**: Configurar a infraestrutura necessária para rate limiting, monitoramento de erros, backups automáticos e tarefas assíncronas.

### Subtasks
- [x] 1.1: Adicionar dependências ao requirements.txt (redis, celery, sentry-sdk, django-ratelimit, django-filter, pytest, pytest-django, pytest-cov)
- [x] 1.2: Criar app/celery.py com configuração do Celery
- [x] 1.3: Atualizar app/__init__.py para importar celery app
- [x] 1.4: Configurar Celery em app/settings.py (CELERY_BROKER_URL, CELERY_RESULT_BACKEND, etc)
- [x] 1.5: Configurar Sentry em app/settings.py (sentry_sdk.init)
- [x] 1.6: Atualizar .env.example com novas variáveis (SENTRY_DSN, REDIS_URL, BACKUP_DIR, APP_VERSION)
- [x] 1.7: Configurar log rotation em app/settings.py (RotatingFileHandler)

## Task 2: Implementar Validadores Customizados
**Requirement IDs**: 2, 9, 10, 14, 22
**Description**: Criar validadores para quantidades, emails, NIF angolano, datas de pagamento e conteúdo de ficheiros.

### Subtasks
- [x] 2.1: Criar app/validators.py com validate_angolan_nif
- [x] 2.2: Adicionar validate_file_content em app/validators.py (magic bytes validation)
- [x] 2.3: Adicionar validate_payment_date em payments/models.py
- [x] 2.4: Criar testes unitários para todos os validadores em tests/test_validators.py

## Task 3: Adicionar Validação de Quantidades Negativas
**Requirement IDs**: 2
**Description**: Implementar validação multi-camada para quantidades em produtos, inflows e outflows.

### Subtasks
- [x] 3.1: Atualizar Product model com MinValueValidator e CheckConstraint
- [x] 3.2: Atualizar Inflow model com MinValueValidator e CheckConstraint
- [x] 3.3: Atualizar Outflow model com MinValueValidator e CheckConstraint
- [x] 3.4: Atualizar Delivery model com MinValueValidator e CheckConstraint
- [x] 3.5: Adicionar clean_quantity em ProductForm, InflowForm, OutflowForm
- [x] 3.6: Criar migration para adicionar CheckConstraints
- [x] 3.7: Criar testes para validação de quantidades negativas

## Task 4: Implementar Controlo de Concorrência em Operações de Stock
**Requirement IDs**: 1
**Description**: Adicionar select_for_update para prevenir race conditions em atualizações de stock.

### Subtasks
- [x] 4.1: Atualizar OutflowCreateView com select_for_update e transaction.atomic
- [x] 4.2: Atualizar OutflowUpdateView com select_for_update e transaction.atomic
- [x] 4.3: Atualizar Delivery.save() com select_for_update e transaction.atomic
- [x] 4.4: Criar testes de concorrência em tests/test_concurrency.py

## Task 5: Implementar Eliminação Atómica de Entregas
**Requirement IDs**: 3
**Description**: Garantir que a eliminação de entregas restaura stock atomicamente.

### Subtasks
- [x] 5.1: Override Delivery.delete() com transaction.atomic e select_for_update
- [x] 5.2: Garantir restauro de stock e atualização de outflow.quantity_delivered
- [x] 5.3: Criar testes para eliminação atómica de entregas

## Task 6: Implementar Sistema de Cache com Invalidação
**Requirement IDs**: 4
**Description**: Adicionar caching ao dashboard com invalidação automática via signals.

### Subtasks
- [x] 6.1: Criar app/cache_utils.py com invalidate_dashboard_cache
- [x] 6.2: Criar products/signals.py com signal handlers para cache invalidation
- [x] 6.3: Adicionar cache invalidation em inflows/signals.py
- [x] 6.4: Adicionar cache invalidation em outflows/signals.py
- [x] 6.5: Adicionar cache invalidation em payments/signals.py
- [x] 6.6: Adicionar cache invalidation em accounts/signals.py
- [x] 6.7: Atualizar app/views.py dashboard com caching
- [x] 6.8: Criar testes para cache invalidation

## Task 7: Implementar Rate Limiting para Autenticação
**Requirement IDs**: 5
**Description**: Adicionar rate limiting para prevenir ataques brute-force no login.

### Subtasks
- [x] 7.1: Criar CustomLoginView em users/views.py com @ratelimit decorator
- [x] 7.2: Configurar RATELIMIT settings em app/settings.py
- [x] 7.3: Atualizar users/urls.py para usar CustomLoginView
- [x] 7.4: Adicionar logging de violações de rate limit
- [x] 7.5: Criar testes para rate limiting

## Task 8: Implementar Proteção CSRF para AJAX
**Requirement IDs**: 6
**Description**: Criar utilitário JavaScript para incluir CSRF token em requisições AJAX.

### Subtasks
- [x] 8.1: Criar app/static/js/csrf.js com getCookie e setupCSRF
- [x] 8.2: Atualizar app/templates/base.html para incluir csrf.js
- [x] 8.3: Verificar todas as views AJAX existentes para CSRF enforcement
- [x] 8.4: Criar testes para CSRF protection

## Task 9: Otimizar Queries com select_related
**Requirement IDs**: 7
**Description**: Adicionar select_related nas views de balance para eliminar N+1 queries.

### Subtasks
- [x] 9.1: Atualizar CustomerBalanceListView.get_queryset() com select_related
- [x] 9.2: Atualizar SupplierBalanceListView.get_queryset() com select_related
- [x] 9.3: Criar testes de performance para verificar redução de queries

## Task 10: Adicionar Índices Compostos na Base de Dados
**Requirement IDs**: 8
**Description**: Criar índices compostos para otimizar queries frequentes.

### Subtasks
- [x] 10.1: Adicionar indexes em CustomerAccountEntry model
- [x] 10.2: Adicionar indexes em SupplierAccountEntry model
- [x] 10.3: Adicionar indexes em Outflow model
- [x] 10.4: Adicionar indexes em Inflow model
- [x] 10.5: Criar migration para adicionar indexes
- [x] 10.6: Criar testes de performance para verificar melhoria com indexes

## Task 11: Melhorar Validação de Email
**Requirement IDs**: 9
**Description**: Adicionar EmailValidator customizado em Customer e Supplier.

### Subtasks
- [x] 11.1: Atualizar Customer.email com EmailValidator
- [x] 11.2: Atualizar Supplier.email com EmailValidator
- [x] 11.3: Criar testes para validação de email

## Task 12: Implementar Validação de NIF Angolano
**Requirement IDs**: 10
**Description**: Adicionar validação de NIF com formato angolano (9 dígitos).

### Subtasks
- [x] 12.1: Atualizar Customer.nif com validate_angolan_nif
- [x] 12.2: Atualizar Supplier.nif com validate_angolan_nif
- [x] 12.3: Atualizar CustomerForm e SupplierForm com validação
- [x] 12.4: Criar testes para validação de NIF

## Task 13: Implementar Backup Automático da Base de Dados
**Requirement IDs**: 13
**Description**: Criar tarefa Celery para backup diário automático com rotação.

### Subtasks
- [x] 13.1: Criar backup_database task em app/tasks.py
- [x] 13.2: Configurar Celery Beat schedule para backup diário às 02:00
- [x] 13.3: Adicionar BACKUP_DIR em app/settings.py
- [x] 13.4: Criar testes para backup task

## Task 14: Implementar Validação de Data de Pagamento
**Requirement IDs**: 14
**Description**: Validar que datas de pagamento não estão no futuro.

### Subtasks
- [x] 14.1: Adicionar clean_date em PaymentForm
- [x] 14.2: Adicionar validate_payment_date em Payment model
- [x] 14.3: Criar testes para validação de data de pagamento

## Task 15: Implementar Cleanup de Thread-Local no Middleware
**Requirement IDs**: 15
**Description**: Garantir cleanup de thread-local storage no AuditMiddleware.

### Subtasks
- [x] 15.1: Atualizar AuditMiddleware com try-finally pattern
- [x] 15.2: Criar helper functions (get_current_user, set_current_user, clear_current_user)
- [x] 15.3: Criar testes para thread-local cleanup

## Task 16: Implementar Exports Paginados
**Requirement IDs**: 16
**Description**: Usar iterator() para exports grandes e delegar para Celery se > 1000 records.

### Subtasks
- [x] 16.1: Criar ExportMixin em reports/views.py com export_csv_streaming
- [x] 16.2: Criar generate_large_excel_export task em reports/tasks.py
- [x] 16.3: Criar generate_large_pdf_export task em reports/tasks.py
- [x] 16.4: Atualizar views de export para usar ExportMixin
- [x] 16.5: Criar TaskStatusView para verificar status de tasks
- [x] 16.6: Criar testes para exports paginados

## Task 17: Implementar Validação de Permissões em Operações Bulk
**Requirement IDs**: 17
**Description**: Adicionar verificação de permissões antes de bulk delete.

### Subtasks
- [x] 17.1: Criar BulkDeleteMixin em app/mixins.py
- [x] 17.2: Atualizar todos os admin.py para usar BulkDeleteMixin
- [x] 17.3: Adicionar logging de operações bulk
- [x] 17.4: Criar testes para validação de permissões

## Task 18: Implementar Exception Handling em Audit Signals
**Requirement IDs**: 18
**Description**: Garantir que falhas em audit logging não quebram operações de negócio.

### Subtasks
- [x] 18.1: Atualizar audit/signals.py com try-except em todos os handlers
- [x] 18.2: Criar create_audit_log helper function com exception handling
- [x] 18.3: Adicionar logging de erros de audit
- [x] 18.4: Criar testes para exception handling em audit

## Task 19: Melhorar Cobertura de Testes
**Requirement IDs**: 19
**Description**: Atingir 80%+ de cobertura de testes com testes unitários abrangentes.

### Subtasks
- [x] 19.1: Criar pytest.ini com configuração de coverage
- [x] 19.2: Reorganizar products/tests/ em package com test_models.py, test_views.py, test_forms.py
- [x] 19.3: Reorganizar inflows/tests/ em package
- [x] 19.4: Reorganizar outflows/tests/ em package
- [x] 19.5: Reorganizar payments/tests/ em package
- [x] 19.6: Reorganizar accounts/tests/ em package
- [x] 19.7: Criar testes para todos os models, forms, views, signals, middleware
- [x] 19.8: Gerar relatório de coverage e verificar 80%+

## Task 20: Criar Suite de Testes de Integração
**Requirement IDs**: 20
**Description**: Criar testes end-to-end para workflows críticos.

### Subtasks
- [x] 20.1: Criar tests/integration/ package
- [x] 20.2: Criar test_outflow_workflow.py com teste completo de outflow e delivery
- [x] 20.3: Criar test_payment_workflow.py com teste de payment e account reconciliation
- [x] 20.4: Criar test_inflow_workflow.py com teste de inflow e stock update
- [x] 20.5: Criar test_auth_workflow.py com teste de authentication e authorization
- [x] 20.6: Criar test_reports.py com teste de report generation
- [x] 20.7: Verificar que suite completa executa em < 5 minutos

## Task 21: Refatorar Código Duplicado em Reports
**Requirement IDs**: 21
**Description**: Criar base classes e mixins para eliminar duplicação em reports.

### Subtasks
- [x] 21.1: Criar BaseReportView em reports/base.py
- [x] 21.2: Criar reports/mixins.py com mixins reutilizáveis
- [x] 21.3: Refatorar CustomerAccountReportView para usar BaseReportView
- [x] 21.4: Refatorar SupplierAccountReportView para usar BaseReportView
- [x] 21.5: Refatorar outras views de reports para usar base classes
- [x] 21.6: Verificar que testes existentes continuam a passar
- [x] 21.7: Medir redução de duplicação (target: 40%+)

## Task 22: Implementar Validação de Magic Bytes em Uploads
**Requirement IDs**: 22
**Description**: Validar conteúdo de ficheiros uploaded por magic bytes.

### Subtasks
- [x] 22.1: Adicionar validate_file_content em app/validators.py
- [x] 22.2: Atualizar Delivery.shipping_guide com validator
- [x] 22.3: Adicionar clean_shipping_guide em DeliveryForm
- [x] 22.4: Criar testes para validação de magic bytes

## Task 23: Implementar Soft Delete para Delivery
**Requirement IDs**: 23
**Description**: Criar sistema de soft delete com possibilidade de restauro.

### Subtasks
- [x] 23.1: Criar SoftDeleteModel, SoftDeleteManager, SoftDeleteQuerySet em app/models.py
- [x] 23.2: Atualizar Delivery model para herdar de SoftDeleteModel
- [x] 23.3: Override Delivery.delete() para soft delete com stock adjustment
- [x] 23.4: Criar Delivery.restore() para restaurar com stock adjustment
- [x] 23.5: Criar DeliveryTrashListView para listar deliveries eliminadas
- [x] 23.6: Criar DeliveryRestoreView para restaurar deliveries
- [x] 23.7: Adicionar URLs para trash e restore
- [x] 23.8: Criar templates para trash list
- [x] 23.9: Criar migration para adicionar is_deleted e deleted_at
- [x] 23.10: Criar testes para soft delete e restore

## Task 24: Adicionar Constraints de Unicidade na Base de Dados
**Requirement IDs**: 24
**Description**: Adicionar unique constraints para NIF e serial_number.

### Subtasks
- [x] 24.1: Adicionar UniqueConstraint em Customer.nif (com condition para null)
- [x] 24.2: Adicionar UniqueConstraint em Supplier.nif (com condition para null)
- [x] 24.3: Adicionar UniqueConstraint em Product.serial_number (com condition para null)
- [x] 24.4: Atualizar CustomerForm para handle IntegrityError
- [x] 24.5: Atualizar SupplierForm para handle IntegrityError
- [x] 24.6: Atualizar ProductForm para handle IntegrityError
- [x] 24.7: Criar migration para adicionar constraints
- [x] 24.8: Criar testes para uniqueness constraints

## Task 25: Configurar Celery Task Queue
**Requirement IDs**: 25
**Description**: Configurar Celery completamente para operações assíncronas.

### Subtasks
- [x] 25.1: Verificar app/celery.py está completo (já criado em Task 1)
- [x] 25.2: Criar task status endpoint em reports/views.py
- [x] 25.3: Configurar email notifications para task completion
- [x] 25.4: Criar testes para Celery tasks

## Task 26: Implementar Filtros Avançados em Reports
**Requirement IDs**: 26
**Description**: Adicionar filtros avançados com django-filter.

### Subtasks
- [x] 26.1: Criar BaseReportFilter em reports/filters.py
- [x] 26.2: Criar OutflowReportFilter com filtros de date range, customer, status
- [x] 26.3: Criar InflowReportFilter com filtros de date range, supplier
- [x] 26.4: Criar PaymentReportFilter com filtros de date range, payment_method
- [x] 26.5: Criar StockReportFilter com filtros de category, low_stock
- [x] 26.6: Atualizar views de reports para usar FilterView
- [x] 26.7: Atualizar templates com forms de filtros
- [x] 26.8: Adicionar django_filters em INSTALLED_APPS
- [x] 26.9: Criar testes para filtros

## Task 27: Implementar Parser de Configuração
**Requirement IDs**: 27
**Description**: Criar parser e serializer para ficheiros de configuração JSON.

### Subtasks
- [x] 27.1: Criar dataclasses em app/config_parser.py (CompanyInfo, DatabaseConfig, etc)
- [x] 27.2: Criar ConfigParser class com parse() method
- [x] 27.3: Criar ConfigPrettyPrinter class com to_json() e to_file()
- [x] 27.4: Criar management command load_config em app/management/commands/
- [x] 27.5: Criar config.example.json
- [x] 27.6: Criar testes para parser (round-trip, validation, error handling)

## Task 28: Documentação e Deployment
**Requirement IDs**: ALL
**Description**: Criar documentação e checklist de deployment.

### Subtasks
- [x] 28.1: Criar README com instruções de setup
- [x] 28.2: Documentar variáveis de ambiente necessárias
- [x] 28.3: Criar guia de deployment
- [x] 28.4: Documentar comandos para iniciar Celery workers
- [x] 28.5: Criar checklist de pré-deployment
- [x] 28.6: Criar checklist de pós-deployment
- [x] 28.7: Documentar procedimento de rollback

## Task 29: Verificação Final e Testes
**Requirement IDs**: ALL
**Description**: Verificar que todos os requisitos foram implementados e testados.

### Subtasks
- [x] 29.1: Executar todos os testes (pytest)
- [x] 29.2: Verificar cobertura de testes ≥ 80%
- [x] 29.3: Executar testes de integração
- [x] 29.4: Verificar que os 93 testes originais continuam a passar
- [x] 29.5: Executar migrations em base de dados de teste
- [x] 29.6: Verificar performance de queries otimizadas
- [x] 29.7: Testar rate limiting manualmente
- [x] 29.8: Testar backup automático
- [x] 29.9: Testar exports grandes
- [x] 29.10: Verificar Sentry integration
- [x] 29.11: Verificar cache invalidation
- [x] 29.12: Criar relatório final de implementação
