# Requirements Document

## Introduction

Este documento especifica os requisitos para implementar melhorias críticas e importantes no Sistema de Gestão de Stocks e Contas (SGE). O sistema Django existente possui 13 modelos, 60+ views e 93 testes, mas análise identificou 27 problemas divididos em três níveis de prioridade:

- **P0 (Crítico)**: 7 problemas de segurança e integridade de dados que devem ser corrigidos imediatamente
- **P1 (Importante)**: 12 problemas de performance, validação e operações que devem ser corrigidos este mês
- **P2-P3 (Melhorias)**: 8 melhorias de qualidade e funcionalidade para implementar em 3 meses

O objetivo é preparar o sistema para produção em larga escala, garantindo segurança, performance, confiabilidade e qualidade.

## Glossary

- **SGE**: Sistema de Gestão de Stocks e Contas
- **System**: O sistema Django SGE completo
- **Race_Condition**: Condição onde múltiplas threads/processos acessam dados compartilhados simultaneamente sem sincronização adequada
- **Select_For_Update**: Mecanismo de lock pessimista do Django ORM que bloqueia linhas da base de dados durante uma transação
- **N_Plus_One_Query**: Anti-padrão onde uma query inicial é seguida por N queries adicionais em loop
- **Rate_Limiter**: Componente que limita o número de requisições por utilizador/IP num período de tempo
- **CSRF_Token**: Cross-Site Request Forgery token para proteger formulários contra ataques
- **Cache_Invalidation**: Processo de remover ou atualizar dados em cache quando os dados originais mudam
- **Atomic_Transaction**: Operação de base de dados que é executada completamente ou não é executada
- **Magic_Bytes**: Primeiros bytes de um ficheiro que identificam o tipo real do ficheiro
- **Soft_Delete**: Marcação de registos como eliminados sem removê-los fisicamente da base de dados
- **Audit_Trail**: Registo cronológico de todas as ações realizadas no sistema
- **Thread_Local**: Armazenamento de dados específico para cada thread de execução
- **OOM**: Out Of Memory - erro quando o sistema fica sem memória disponível
- **Sentry**: Plataforma de monitoramento de erros e performance
- **Celery**: Sistema de filas de tarefas assíncronas para Python
- **NIF**: Número de Identificação Fiscal angolano
- **Brute_Force_Attack**: Ataque que tenta adivinhar credenciais através de tentativas repetidas

## Requirements

### Requirement 1: Concurrency Control in Stock Operations

**User Story:** As a system administrator, I want stock operations to be protected against race conditions, so that concurrent transactions cannot create inconsistent stock levels.

#### Acceptance Criteria

1. WHEN multiple concurrent requests attempt to update the same Product stock, THE System SHALL use Select_For_Update to serialize access
2. WHEN OutflowUpdateView processes a form, THE System SHALL acquire a database lock on the Product before validating stock availability
3. FOR ALL concurrent stock update operations, executing N operations that each decrement stock by X SHALL result in total stock decrease of exactly N*X (linearizability property)
4. IF a transaction attempts to acquire a lock on an already-locked Product, THEN THE System SHALL wait until the lock is released or timeout occurs
5. WHEN a stock validation fails within a locked transaction, THE System SHALL rollback all changes and release the lock

### Requirement 2: Negative Quantity Validation

**User Story:** As a data integrity officer, I want all quantity inputs to be validated as non-negative, so that the system cannot accept invalid data.

#### Acceptance Criteria

1. WHEN ProductForm receives a negative quantity value, THE System SHALL reject the form with a descriptive error message
2. WHEN InflowForm receives a quantity <= 0, THE System SHALL reject the form with error "Quantidade deve ser maior que zero"
3. WHEN OutflowForm receives a quantity <= 0, THE System SHALL reject the form with error "Quantidade deve ser maior que zero"
4. WHEN DeliveryConfirmWeightView receives a negative actual_quantity, THE System SHALL reject the form with a descriptive error
5. FOR ALL quantity input fields, THE System SHALL enforce validation at both form level and database constraint level
6. FOR ALL valid quantity inputs Q, submitting Q then retrieving the saved value SHALL return exactly Q (round-trip property)

### Requirement 3: Atomic Delivery Deletion

**User Story:** As a system administrator, I want delivery deletions to be atomic, so that stock adjustments and database changes are consistent.

#### Acceptance Criteria

1. WHEN Delivery.delete() is called, THE System SHALL wrap all operations in an Atomic_Transaction
2. WHEN a Delivery is deleted, THE System SHALL restore the Product stock by the final_quantity amount within the same transaction
3. WHEN a Delivery is deleted, THE System SHALL update the parent Outflow.quantity_delivered within the same transaction
4. IF any operation within the deletion transaction fails, THEN THE System SHALL rollback all changes including stock restoration
5. FOR ALL Delivery deletions, creating a Delivery with quantity Q then deleting it SHALL restore stock to original level (inverse property)

### Requirement 4: Dashboard Cache Invalidation

**User Story:** As a user, I want the dashboard to show current data, so that I can make decisions based on accurate information.

#### Acceptance Criteria

1. WHEN a Product is created, updated, or deleted, THE System SHALL invalidate the dashboard cache
2. WHEN an Inflow is created or deleted, THE System SHALL invalidate the dashboard cache
3. WHEN an Outflow is created, updated, or deleted, THE System SHALL invalidate the dashboard cache
4. WHEN a Delivery is created, updated, or deleted, THE System SHALL invalidate the dashboard cache
5. WHEN a Payment is created or deleted, THE System SHALL invalidate the dashboard cache
6. WHEN an AccountEntry is created or deleted, THE System SHALL invalidate the dashboard cache
7. FOR ALL cache invalidation events, the next dashboard request SHALL fetch fresh data from the database

### Requirement 5: Authentication Rate Limiting

**User Story:** As a security officer, I want login attempts to be rate-limited, so that brute-force attacks are prevented.

#### Acceptance Criteria

1. WHEN a user attempts to login, THE Rate_Limiter SHALL track attempts by username and IP address
2. WHEN a user exceeds 5 failed login attempts within 15 minutes, THE System SHALL block further attempts for 30 minutes
3. WHEN a successful login occurs, THE System SHALL reset the failed attempt counter for that user
4. WHEN a rate limit is exceeded, THE System SHALL return HTTP 429 with a descriptive message indicating wait time
5. WHEN the rate limit cooldown period expires, THE System SHALL allow login attempts again
6. THE System SHALL log all rate limit violations with timestamp, username, and IP address

### Requirement 6: CSRF Protection for AJAX Requests

**User Story:** As a security officer, I want AJAX requests to include CSRF tokens, so that the application is protected against CSRF attacks.

#### Acceptance Criteria

1. WHEN an AJAX POST request is made, THE System SHALL include the CSRF_Token in the request headers
2. WHEN an AJAX request is received without a valid CSRF_Token, THE System SHALL reject it with HTTP 403
3. THE System SHALL provide a JavaScript utility function to automatically attach CSRF_Token to all AJAX requests
4. WHEN a form is submitted via AJAX, THE System SHALL validate the CSRF_Token before processing
5. FOR ALL AJAX endpoints that modify data, THE System SHALL enforce CSRF protection

### Requirement 7: Query Optimization for Account Balance Views

**User Story:** As a user, I want account balance pages to load quickly, so that I can access financial information efficiently.

#### Acceptance Criteria

1. WHEN CustomerBalanceListView is rendered, THE System SHALL use select_related to fetch related Outflow and Payment data in a single query
2. WHEN SupplierBalanceListView is rendered, THE System SHALL use select_related to fetch related Inflow and Payment data in a single query
3. FOR ALL balance list views, THE System SHALL execute at most 3 database queries regardless of the number of entries displayed
4. WHEN a balance view displays N entries, THE System SHALL NOT execute N+1 queries (N_Plus_One_Query prevention)
5. THE System SHALL add database indexes on (customer_id, created_at) and (supplier_id, created_at) for CustomerAccountEntry and SupplierAccountEntry

### Requirement 8: Composite Database Indexes

**User Story:** As a database administrator, I want composite indexes on frequently queried columns, so that query performance is optimized.

#### Acceptance Criteria

1. THE System SHALL create a composite index on CustomerAccountEntry(customer, created_at)
2. THE System SHALL create a composite index on SupplierAccountEntry(supplier, created_at)
3. THE System SHALL create a composite index on Outflow(customer, created_at)
4. THE System SHALL create a composite index on Inflow(supplier, created_at)
5. WHEN queries filter by customer/supplier and order by created_at, THE System SHALL use the composite indexes
6. FOR ALL indexed queries, execution time SHALL be reduced by at least 50% compared to non-indexed queries on datasets with 1000+ records

### Requirement 9: Email Validation Enhancement

**User Story:** As a data quality officer, I want email addresses to be validated with proper format checking, so that only valid emails are stored.

#### Acceptance Criteria

1. WHEN a Customer or Supplier email is provided, THE System SHALL validate it using Django's EmailValidator
2. WHEN an invalid email format is submitted, THE System SHALL reject it with error "Introduza um endereço de email válido"
3. THE System SHALL accept valid email formats including: user@domain.com, user.name@domain.co.ao, user+tag@domain.com
4. THE System SHALL reject invalid formats including: @domain.com, user@, user@domain, user domain@test.com
5. FOR ALL valid email addresses E, submitting E then retrieving it SHALL return exactly E (round-trip property)

### Requirement 10: Angolan NIF Validation

**User Story:** As a compliance officer, I want customer and supplier NIF numbers to be validated according to Angolan format, so that tax identification is accurate.

#### Acceptance Criteria

1. WHEN a Customer or Supplier NIF is provided, THE System SHALL validate it follows the Angolan NIF format
2. THE System SHALL accept NIF in format: 9 digits (e.g., "123456789")
3. THE System SHALL reject NIF with non-numeric characters
4. THE System SHALL reject NIF with length different from 9 digits
5. WHEN an invalid NIF is submitted, THE System SHALL return error "NIF deve conter exatamente 9 dígitos numéricos"
6. THE System SHALL allow NIF to be optional (null/blank) but validate format when provided

### Requirement 11: Log Rotation Configuration

**User Story:** As a system administrator, I want application logs to be automatically rotated, so that disk space is managed efficiently.

#### Acceptance Criteria

1. THE System SHALL use RotatingFileHandler for all log files
2. WHEN a log file reaches 10 MB, THE System SHALL rotate it to a backup file
3. THE System SHALL maintain a maximum of 5 backup log files
4. WHEN the maximum number of backups is reached, THE System SHALL delete the oldest backup before creating a new one
5. THE System SHALL name rotated logs with pattern: django.log, django.log.1, django.log.2, etc.
6. FOR ALL log rotation operations, no log entries SHALL be lost during rotation

### Requirement 12: Error Monitoring Integration

**User Story:** As a development team, I want application errors to be automatically reported to Sentry, so that we can proactively fix issues.

#### Acceptance Criteria

1. WHEN an unhandled exception occurs, THE System SHALL send error details to Sentry
2. THE System SHALL include in error reports: stack trace, request context, user information, and environment variables
3. WHEN Sentry integration is enabled, THE System SHALL initialize the Sentry SDK on application startup
4. THE System SHALL configure Sentry DSN via environment variable SENTRY_DSN
5. WHERE Sentry is not configured, THE System SHALL log errors locally without failing
6. THE System SHALL capture errors with severity level ERROR and above
7. THE System SHALL set Sentry environment tag based on DEBUG setting (development/production)

### Requirement 13: Automated Database Backup

**User Story:** As a system administrator, I want database backups to run automatically on a schedule, so that data is protected without manual intervention.

#### Acceptance Criteria

1. THE System SHALL provide a Celery task for automated database backup
2. WHEN the backup task runs, THE System SHALL create a timestamped copy of the database file
3. THE System SHALL schedule the backup task to run daily at 02:00 AM
4. WHEN a backup is created, THE System SHALL verify the backup file is readable and non-empty
5. THE System SHALL maintain the last 30 daily backups and delete older backups
6. WHEN a backup fails, THE System SHALL log the error and send a notification via Sentry
7. THE System SHALL store backups in a configurable directory specified by BACKUP_DIR environment variable

### Requirement 14: Future Date Validation for Payments

**User Story:** As a financial controller, I want payment dates to be validated against future dates, so that payments cannot be recorded with impossible dates.

#### Acceptance Criteria

1. WHEN a Payment date is provided, THE System SHALL validate it is not in the future
2. WHEN a payment date is more than 1 day in the future, THE System SHALL reject it with error "Data de pagamento não pode ser no futuro"
3. THE System SHALL allow payment dates up to the current date (today)
4. THE System SHALL allow payment dates in the past without restriction
5. FOR ALL payment date validations, THE System SHALL use timezone-aware comparison based on Africa/Luanda timezone

### Requirement 15: Thread-Local Cleanup in Audit Middleware

**User Story:** As a system administrator, I want thread-local storage to be properly cleaned up, so that memory leaks and cross-request contamination are prevented.

#### Acceptance Criteria

1. WHEN AuditMiddleware processes a request, THE System SHALL set the current user in thread-local storage
2. WHEN the request completes (success or failure), THE System SHALL clear the thread-local user reference
3. WHEN an exception occurs during request processing, THE System SHALL still clear thread-local storage in the finally block
4. FOR ALL requests, thread-local storage SHALL be empty before the next request starts (isolation property)
5. THE System SHALL use try-finally pattern to guarantee cleanup even when exceptions occur

### Requirement 16: Paginated Export Operations

**User Story:** As a user, I want to export large datasets without causing memory issues, so that the system remains stable during exports.

#### Acceptance Criteria

1. WHEN an export operation processes more than 1000 records, THE System SHALL use iterator() or chunked queries
2. WHEN generating Excel exports, THE System SHALL process records in batches of 500
3. WHEN generating PDF exports, THE System SHALL process records in batches of 100
4. THE System SHALL not load all export records into memory simultaneously
5. FOR ALL export operations with N records, memory usage SHALL remain constant regardless of N (streaming property)
6. WHEN an export operation exceeds 60 seconds, THE System SHALL delegate it to a Celery background task

### Requirement 17: Permission Validation for Bulk Operations

**User Story:** As a security officer, I want bulk delete operations to validate permissions, so that unauthorized users cannot delete multiple records.

#### Acceptance Criteria

1. WHEN a bulk delete operation is requested, THE System SHALL verify the user has delete permission for the model
2. WHEN a user lacks delete permission, THE System SHALL reject the operation with HTTP 403
3. THE System SHALL validate permissions before executing any database deletions
4. WHEN bulk deleting N records, THE System SHALL verify permission once (not N times)
5. THE System SHALL log all bulk delete operations with user, timestamp, and number of records affected

### Requirement 18: Exception Handling in Audit Signals

**User Story:** As a system administrator, I want audit logging failures to not break business operations, so that the system remains available even when audit logging fails.

#### Acceptance Criteria

1. WHEN an audit signal handler encounters an exception, THE System SHALL log the error and continue processing
2. WHEN audit log creation fails, THE System SHALL not rollback the business transaction
3. THE System SHALL wrap all audit signal logic in try-except blocks
4. WHEN an audit exception occurs, THE System SHALL log it with severity ERROR including the original exception details
5. FOR ALL business operations, audit logging failures SHALL not prevent the operation from completing (resilience property)

### Requirement 19: Test Coverage Improvement

**User Story:** As a development team, I want comprehensive test coverage, so that we can refactor and add features with confidence.

#### Acceptance Criteria

1. THE System SHALL achieve minimum 80% code coverage across all applications
2. THE System SHALL include unit tests for all model methods and properties
3. THE System SHALL include unit tests for all form validation logic
4. THE System SHALL include integration tests for all critical user workflows
5. THE System SHALL include tests for all signal handlers
6. THE System SHALL include tests for all middleware components
7. THE System SHALL include tests for all custom template tags and filters
8. WHEN tests are run, THE System SHALL generate a coverage report showing coverage percentage per module

### Requirement 20: Integration Test Suite

**User Story:** As a QA engineer, I want integration tests for critical workflows, so that end-to-end functionality is verified.

#### Acceptance Criteria

1. THE System SHALL include integration tests for the complete outflow creation and delivery workflow
2. THE System SHALL include integration tests for the payment and account reconciliation workflow
3. THE System SHALL include integration tests for the inflow and stock update workflow
4. THE System SHALL include integration tests for user authentication and authorization
5. THE System SHALL include integration tests for report generation with real data
6. FOR ALL integration tests, THE System SHALL use Django's TransactionTestCase to ensure database isolation
7. WHEN integration tests run, THE System SHALL complete in less than 5 minutes

### Requirement 21: Code Duplication Refactoring

**User Story:** As a developer, I want duplicated code to be refactored into reusable components, so that maintenance is easier.

#### Acceptance Criteria

1. WHEN report views share common logic, THE System SHALL extract it into a base class or mixin
2. THE System SHALL create a BaseReportView with common functionality for filtering, pagination, and export
3. THE System SHALL refactor customer_account_report and supplier_account_report to use shared logic
4. THE System SHALL refactor outflows_by_customer_report and deliveries_report to use shared logic
5. FOR ALL refactored code, existing tests SHALL continue to pass without modification
6. THE System SHALL reduce code duplication in reports module by at least 40%

### Requirement 22: File Upload Magic Bytes Validation

**User Story:** As a security officer, I want uploaded files to be validated by content (magic bytes), so that malicious files disguised with wrong extensions are rejected.

#### Acceptance Criteria

1. WHEN a shipping guide file is uploaded, THE System SHALL validate the file content matches the declared extension
2. THE System SHALL verify PDF files start with magic bytes: %PDF
3. THE System SHALL verify JPEG files start with magic bytes: FF D8 FF
4. THE System SHALL verify PNG files start with magic bytes: 89 50 4E 47
5. WHEN file content does not match the extension, THE System SHALL reject the upload with error "Tipo de arquivo inválido"
6. THE System SHALL perform magic bytes validation before saving the file to disk
7. FOR ALL valid file uploads, THE System SHALL verify both extension and content type match

### Requirement 23: Soft Delete for Delivery Model

**User Story:** As a user, I want deleted deliveries to be recoverable, so that accidental deletions can be undone.

#### Acceptance Criteria

1. THE Delivery model SHALL inherit from SoftDeleteModel
2. WHEN Delivery.delete() is called, THE System SHALL set is_deleted=True instead of removing the record
3. THE System SHALL provide a DeliveryTrashListView to display soft-deleted deliveries
4. THE System SHALL provide a restore action to recover soft-deleted deliveries
5. THE System SHALL provide a hard_delete action for permanent deletion (admin only)
6. WHEN a Delivery is soft-deleted, THE System SHALL still adjust stock and update Outflow.quantity_delivered
7. WHEN a Delivery is restored, THE System SHALL reverse the stock adjustment
8. FOR ALL soft-delete operations, creating then soft-deleting then restoring a Delivery SHALL result in the same system state (idempotence property)

### Requirement 24: Database Uniqueness Constraints

**User Story:** As a data integrity officer, I want unique constraints enforced at database level, so that duplicate data cannot be created even in race conditions.

#### Acceptance Criteria

1. THE System SHALL add a unique constraint on Customer.nif (when not null)
2. THE System SHALL add a unique constraint on Supplier.nif (when not null)
3. THE System SHALL add a unique constraint on Product.serial_number (when not null)
4. WHEN a duplicate NIF is submitted, THE System SHALL reject it with error "Já existe um cliente/fornecedor com este NIF"
5. WHEN a duplicate serial number is submitted, THE System SHALL reject it with error "Já existe um produto com este número de série"
6. FOR ALL uniqueness constraints, concurrent attempts to create duplicates SHALL result in exactly one success and N-1 failures

### Requirement 25: Celery Task Queue for Async Operations

**User Story:** As a user, I want long-running operations to execute in the background, so that the web interface remains responsive.

#### Acceptance Criteria

1. THE System SHALL configure Celery with Redis as the message broker
2. THE System SHALL provide a Celery task for generating large Excel exports
3. THE System SHALL provide a Celery task for generating large PDF reports
4. THE System SHALL provide a Celery task for automated database backups
5. WHEN a background task is submitted, THE System SHALL return immediately with a task ID
6. THE System SHALL provide a task status endpoint to check task progress
7. WHEN a background task completes, THE System SHALL notify the user via email or in-app notification
8. THE System SHALL configure Celery Beat for scheduled periodic tasks
9. THE System SHALL configure task result backend to store task results for 24 hours

### Requirement 26: Advanced Report Filters

**User Story:** As a user, I want advanced filtering options in reports, so that I can analyze specific data segments.

#### Acceptance Criteria

1. THE System SHALL provide date range filters (start_date, end_date) for all reports
2. THE System SHALL provide customer/supplier filters for account reports
3. THE System SHALL provide product category filter for stock reports
4. THE System SHALL provide status filter (pending/partial/delivered) for outflow reports
5. THE System SHALL provide payment method filter for payment reports
6. WHEN multiple filters are applied, THE System SHALL combine them with AND logic
7. THE System SHALL preserve filter values in the URL query string for bookmarking
8. THE System SHALL display active filters with a "clear filters" option
9. FOR ALL filter combinations, THE System SHALL return results in less than 2 seconds for datasets up to 10,000 records

### Requirement 27: Parser and Serializer for Configuration

**User Story:** As a developer, I want to parse and serialize system configuration files, so that settings can be managed programmatically.

#### Acceptance Criteria

1. WHEN a valid JSON configuration file is provided, THE Config_Parser SHALL parse it into a Configuration object
2. WHEN an invalid JSON configuration file is provided, THE Config_Parser SHALL return a descriptive error with line number
3. THE Config_Pretty_Printer SHALL format Configuration objects back into valid JSON files with proper indentation
4. FOR ALL valid Configuration objects C, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
5. THE Config_Parser SHALL validate required fields: COMPANY_INFO, DATABASE, CACHE, LOGGING
6. THE Config_Parser SHALL validate field types match the expected schema
7. WHEN configuration is loaded, THE System SHALL apply it to Django settings
