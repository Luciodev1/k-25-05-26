# Changelog - SGE (Sistema de Gestao de Stocks e Contas)

Todas as modificacoes, melhorias e correcoes aplicadas ao projeto.

---

## 2026-05-21 — Correcoes e Melhorias

### P0 — Seguranca e Integridade

#### 1. Race condition no OutflowCreateView
- **Ficheiro:** `outflows/views.py`
- **Problema:** `OutflowForm.clean()` validava stock sem lock de BD. Dois outflows concorrentes podiam ambos passar a validacao e exceder o stock disponivel.
- **Solucao:** `OutflowCreateView.form_valid()` agora envolve a logica em `transaction.atomic()` com `Product.objects.select_for_update().get(...)` para bloquear a linha do produto durante a verificacao. Padrao consistente com `DeliveryCreateView`.

#### 2. Headers de seguranca para producao
- **Ficheiro:** `app/settings.py`
- **Problema:** Faltavam headers HSTS, SSL redirect e hardening de cookies.
- **Solucao:** Adicionado (condicional `if not DEBUG`):
  - `SECURE_HSTS_SECONDS = 31536000` (1 ano)
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
  - `SECURE_HSTS_PRELOAD = True`
  - `SECURE_SSL_REDIRECT = True`
  - `CSRF_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_HTTPONLY = True`

### P1 — Acesso e Performance

#### 3. Permissoes nas views de contas
- **Ficheiro:** `accounts/views.py`
- **Problema:** `CustomerAccountListView`, `SupplierAccountListView`, `CustomerBalanceListView` e `SupplierBalanceListView` exigiam apenas `LoginRequiredMixin`. Qualquer utilizador autenticado podia aceder a dados financeiros.
- **Solucao:** Adicionado `PermissionRequiredMixin` com `permission_required = 'payments.view_payment'` nas 4 views.

#### 4. Paginacao nos relatorios
- **Ficheiros:** `reports/views.py`, `reports/templates/report_outflows_by_customer.html`, `report_customer_account.html`, `report_supplier_account.html`, `report_deliveries.html`
- **Problema:** Relatorios carregavam todos os registos sem paginacao — full table scans com datasets grandes.
- **Solucao:** Adicionado `Paginator(queryset, 20)` nas 4 views de relatorio (`outflows_by_customer_report`, `deliveries_report`, `customer_account_report`, `supplier_account_report`). Templates atualizados com componente `components/_pagination.html`. Exportacoes Excel/PDF mantêm todos os registos.

### P2 — Validacao e Configuracao

#### 5. Validacao de uploads (shipping guide)
- **Ficheiros:** `outflows/models.py`, `outflows/forms.py`
- **Problema:** `Delivery.shipping_guide_file` aceitava qualquer ficheiro sem validacao de tipo ou tamanho.
- **Solucao:**
  - Model: `FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])` + `validate_file_size` (max 10 MB)
  - Form: `DeliveryForm.clean_shipping_guide_file()` valida `content_type` e `size`

#### 6. STATIC_ROOT para WhiteNoise
- **Ficheiro:** `app/settings.py`
- **Problema:** `STATIC_ROOT` nao definido — `collectstatic` falhava em producao.
- **Solucao:** Adicionado `STATIC_ROOT = BASE_DIR / 'staticfiles'`.

#### 7. Bug na paginacao de extratos (full_description perdido)
- **Ficheiros:** `reports/views.py`, `reports/templates/report_customer_account.html`, `reports/templates/report_supplier_account.html`
- **Problema:** `full_description` era atributo Python definido em instancias do queryset, mas `annotate()` + `Paginator` criam novas instancias que perdem esse atributo. Coluna Descricao ficava vazia na paginacao.
- **Solucao:** Logica de descricao movida para o template (`{% if e.outflow %}...{% endif %}`). Loop `full_description` removido das views.

---

## P0 - Correcoes Criticas (Seguranca e Integridade de Dados)

### 1. Race condition no DeliveryConfirmWeightView
- **Ficheiro:** `outflows/views.py`
- **Problema:** O stock era ajustado multiplas vezes devido a conflito entre o signal e a view. O `select_for_update()` nao era usado, permitindo concorrencia.
- **Solucao:** Adicionado `select_for_update()` na `DeliveryConfirmWeightView` e `DeliveryCreateView` para garantir atomicidade. Os updates usam `F()` expressions para operacoes atomicas na BD.

### 2. Signal usa `final_quantity` em vez de `quantity`
- **Ficheiro:** `outflows/signals.py`
- **Problema:** O signal `update_stock_on_delivery_save` usava `instance.quantity` (quantidade estimada) em vez de `instance.final_quantity` (quantidade real quando confirmada).
- **Solucao:** Alterado para `instance.final_quantity` nos signals de `post_save` e `post_delete`.

### 3. SECRET_KEY e DEBUG hardcoded
- **Ficheiro:** `app/settings.py`
- **Problema:** `SECRET_KEY` exposta no codigo com prefixo `django-insecure-`. `DEBUG = True` sem protecao. `ALLOWED_HOSTS = []` causava erro em producao.
- **Solucao:** Movidos para variaveis de ambiente (`os.environ.get`):
  - `DJANGO_SECRET_KEY`
  - `DJANGO_DEBUG`
  - `DJANGO_ALLOWED_HOSTS`

### 4. Conflito entre signals de accounts e payments
- **Ficheiro:** `accounts/signals.py`, `payments/signals.py`
- **Problema:** A eliminacao de uma `Outflow` removia o debito mas deixava creditos orfaos de pagamentos associados. O `payments/signals.py` usava `post_delete`, mas o `SET_NULL` ja nulificava o campo antes do signal disparar.
- **Solucao:**
  - `accounts/signals.py`: Alterado de `post_delete` para `pre_delete` com `transaction.atomic()`
  - `payments/signals.py`: Alterado de `post_delete` para `pre_delete` para eliminar entradas de conta antes do `SET_NULL`

### 5. CheckConstraint para stock negativo
- **Ficheiro:** `products/models.py`
- **Problema:** Nenhum mecanismo impedir `Product.quantity` de ficar negativo.
- **Solucao:** Adicionado `CheckConstraint` com `condition=models.Q(quantity__gte=0)` no Meta do modelo. Constraint aplicada a nivel da BD.

---

## P1 - Correcoes Importantes (Performance e Consistencia)

### 6. Dashboard otimizado com aggregate
- **Ficheiro:** `app/views.py`
- **Problema:** O dashboard carregava TODOS os clientes/suppliers em memoria para calcular totais financeiros usando Python loops.
- **Solucao:** Substituido por `aggregate()` com `Coalesce(Sum(...), Value(Decimal('0')))` diretamente na BD. Corrigido erro de tipos mistos (`DecimalField` vs `IntegerField`) usando `Value(Decimal('0'))`.

### 7. Expressao com tipos mistos no stock value
- **Ficheiro:** `app/views.py`
- **Problema:** `F('quantity') * F('selling_price')` causava `FieldError: Expression contains mixed types: DecimalField, IntegerField`.
- **Solucao:** Substituido por calculo em Python: `sum(p.quantity * p.selling_price for p in Product.objects.only(...))`.

### 8. select_related em queries com FK
- **Ficheiro:** `accounts/views.py`, `outflows/views.py`
- **Problema:** N+1 queries em `CustomerAccountListView`, `SupplierAccountListView` e `OutflowDetailView`.
- **Solucao:** Adicionado `select_related('outflow__product', 'payment')` nas queries.

### 9. TIME_ZONE corrigido
- **Ficheiro:** `app/settings.py`
- **Problema:** `TIME_ZONE = 'UTC'` para uma app em Angola (UTC+1).
- **Solucao:** Alterado para `TIME_ZONE = 'Africa/Luanda'`.

### 10. Trailing slashes inconsistentes nos URLs
- **Ficheiros:** `products/urls.py`, `customers/urls.py`, `inflows/urls.py`, `outflows/urls.py`
- **Problema:** Alguns URLs nao tinham trailing slash (`/products/list` vs `/products/list/`).
- **Solucao:** Adicionado trailing slash a todos os URL patterns.

---

## P2 - Melhorias de Qualidade

### 11. Imports limpos no dashboard
- **Ficheiro:** `app/views.py`
- **Problema:** Imports nao usados (`Abs`, `Case`, `When`, `DecimalField`).
- **Solucao:** Removidos imports redundantes.

### 12. Category.name reduzido
- **Ficheiro:** `categories/models.py`
- **Problema:** `max_length=500` para um nome de categoria era excessivo.
- **Solucao:** Alterado para `max_length=200`.

### 13. Templates 404 e 500
- **Ficheiros:** `app/templates/404.html`, `app/templates/500.html`
- **Problema:** Nao existiam templates de erro customizados.
- **Solucao:** Criados templates com design consistente. O template 500 nao usa `{% url %}` nem `{% static %}` para evitar falhas sem contexto.

### 14. TEMPLATES DIRS usa Path
- **Ficheiro:** `app/settings.py`
- **Problema:** `'DIRS': ['app/templates']` usava string em vez de Path.
- **Solucao:** Alterado para `'DIRS': [BASE_DIR / 'app' / 'templates']`.

---

## P3 - Seguranca

### 15. Settings de seguranca para producao
- **Ficheiro:** `app/settings.py`
- **Adicionado** (condicional `if not DEBUG`):
  - `CSRF_COOKIE_SECURE = True`
  - `SESSION_COOKIE_SECURE = True`
  - `SECURE_BROWSER_XSS_FILTER = True`
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`
  - `X_FRAME_OPTIONS = 'DENY'`

---

## P4 - Robustez e Qualidade

### 16. Suite de testes (24 testes)
- **Ficheiros:** `products/tests.py`, `inflows/tests.py`, `outflows/tests.py`, `accounts/tests.py`, `payments/tests.py`
- **Testes criados:**
  - `products`: 3 testes (criacao, default quantity, CheckConstraint)
  - `inflows`: 3 testes (stock increase, delete restore, acumulacao)
  - `outflows`: 8 testes (stock delivery, quantity_delivered, delete, multiplas entregas, status, confirm weight)
  - `accounts`: 4 testes (debit/credit entries, delete cleanup)
  - `payments`: 6 testes (receipt/payment entries, delete, metodos, form validation)

### 17. Logging configurado
- **Ficheiro:** `app/settings.py`
- **Adicionado:** Configuracao de `LOGGING` com:
  - Handler `file`: escreve em `logs/django.log` (WARNING+)
  - Handler `console`: output para terminal (DEBUG em dev, WARNING em prod)
  - Formatters `verbose` e `simple`

### 18. requirements.txt
- **Ficheiro:** `requirements.txt` (novo)
- **Conteudo:** Django, openpyxl, reportlab, pillow, pypdf, xhtml2pdf, whitenoise

---

## P5 - Produtividade e Performance

### 19. Admin site completo
- **Ficheiro:** `drivers/admin.py`
- **Problema:** `DriverAdmin` nao estava registado.
- **Solucao:** Adicionado `@admin.register(models.Driver)` com `list_display` e `search_fields`.

### 20. .env.example
- **Ficheiro:** `.env.example` (novo)
- **Conteudo:** Documentacao das variaveis de ambiente necessarias (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`).

---

## P6 - Funcionalidade

### 21. Error handlers customizados
- **Ficheiros:** `app/views.py`, `app/urls.py`, `app/templates/500.html`
- **Adicionado:** Views `custom_404` e `custom_500` com logging. Handler declarations em `urls.py`. Template 500 simplificado (sem template tags que dependem de contexto).

### 22. DetailView para drivers e payments
- **Ficheiros:** `drivers/views.py`, `drivers/urls.py`, `drivers/templates/driver_detail.html`, `payments/views.py`, `payments/urls.py`, `payments/templates/payment_detail.html`
- **Adicionado:** `DriverDetailView` e `PaymentDetailView` com templates detalhados e URLs com trailing slash.

### 23. Validacao reforcada em forms
- **Ficheiros:** `inflows/forms.py`, `outflows/forms.py`
- **Adicionado:**
  - `InflowForm.clean_quantity()`: valida quantidade > 0
  - `OutflowForm.clean_quantity()`: valida quantidade > 0
  - `OutflowForm.clean()`: valida quantidade <= stock disponivel

### 24. Whitenoise para static files
- **Ficheiros:** `app/settings.py`, `requirements.txt`
- **Adicionado:** `whitenoise.middleware.WhiteNoiseMiddleware` no MIDDLEWARE (depois de SecurityMiddleware). Pacote `whitenoise` no requirements.txt.

### 25. Management command de backup
- **Ficheiros:** `products/management/commands/backup_db.py` (novo)
- **Comando:** `python manage.py backup_db [--output-dir PATH]`
- **Funcionalidades:**
  - Copia `db.sqlite3` com timestamp
  - Mantem ultimos 10 backups (limpa os antigos)
  - Logging de operacoes

---

## P7 - Funcionalidade Avancada

### 26. Audit trail
- **Ficheiros:** `audit/` (app completo - 8 ficheiros)
  - `audit/models.py`: Modelo `AuditLog` com campos `user`, `action`, `model_name`, `object_id`, `object_repr`, `changes` (JSON), `timestamp`
  - `audit/signals.py`: Signals para registar CREATE/DELETE em 10 modelos monitorados
  - `audit/middleware.py`: `AuditMiddleware` para capturar utilizador atual via thread-local
  - `audit/views.py`: `AuditLogListView` com filtros por acao/modelo/utilizador
  - `audit/admin.py`: `AuditLogAdmin` read-only com date_hierarchy
  - `audit/urls.py`: URL `/auditoria/`
  - `audit/templates/audit_list.html`: Tabela de logs com filtros
  - `audit/apps.py`: `AuditConfig` com `ready()` para carregar signals

### 27. Notificacoes reais
- **Ficheiros:** `audit/templatetags/notification_tags.py` (novo), `app/templates/components/_header.html`
- **Problema:** Header tinha 3 notificacoes hardcoded.
- **Solucao:** Templatetag `get_notifications` que retorna alertas dinamicos:
  - Stock baixo (<= 10 unidades)
  - Produtos sem stock
  - Entregas pendentes
  - Contas a receber
  - Contas a pagar
- Header atualizado para usar notificacoes reais com badge de contagem.

### 28. Pesquisa global
- **Ficheiros:** `app/views.py`, `app/urls.py`, `app/templates/global_search.html` (novo)
- **Funcionalidade:** Busca transversal em 7 modelos:
  - Produtos (por titulo, numero de serie)
  - Clientes (por nome, NIF, telefone)
  - Fornecedores (por nome)
  - Saidas (por produto, cliente)
  - Motoristas (por nome, matricula)
  - Marcas (por nome)
  - Categorias (por nome)
- URL: `/pesquisa/?q=termo`
- Template com resultados agrupados por tipo, icones e links diretos.

### 29. Sidebar atualizada
- **Ficheiro:** `app/templates/components/_sidebar.html`
- **Adicionado:** Secao "Sistema" com links para:
  - Auditoria (`/auditoria/`)
  - Utilizadores (`/users/`) - visivel apenas com permissao `auth.view_user`

---

## Migrations Geradas

| App | Migration | Descricao |
|---|---|---|
| `products` | `0005_product_product_quantity_non_negative` | CheckConstraint stock >= 0 |
| `accounts` | `0006_alter_customeraccountentry_outflow_and_more` | Revert para SET_NULL |
| `categories` | `0002_alter_category_name` | name max_length 500 -> 200 |
| `audit` | `0001_initial` | Criacao do modelo AuditLog |

---

---

## 2026-05-26 — Isolamento Multi-Empresa (Tenant Isolation)

### Arquitetura de Multi-Tenancy

Implementado isolamento completo por empresa (`Tenant`) em toda a aplicacao. Cada utilizador pertence a uma ou mais empresas atraves do modelo `TenantUser`. O tenant ativo e armazenado na sessao e disponibilizado via `request.tenant`.

#### Modelo de Dados

- **`tenants/models.py`:** Modelos `Tenant` (UUID PK, nome, slug, config), `TenantUser` (user M2M com role), `TenantSettings` (config por tenant)
- **`tenants/middleware.py`:** `TenantMiddleware` — define `request.tenant` e `request.tenant_user` em cada request
- **`tenants/context_processors.py`:** `current_tenant` — disponibiliza `current_tenant`, `tenant_user`, `available_tenants` em todos os templates
- **`app/mixins.py`:** `TenantFilterMixin` — `get_queryset()` filtra por tenant, `form_valid()` define tenant no objeto

### P0 — Seguranca e Isolamento

#### 1. Middleware bloqueia utilizadores sem empresa

- **Ficheiro:** `tenants/middleware.py`
- **Problema:** Utilizadores autenticados sem `TenantUser` associado navegavam pelo sistema vendo ecras vazios (confuso), e se algum modelo tivesse `tenant=None`, dados podiam vazar.
- **Solucao:**
  - Se utilizador tem **0 empresas** (e nao e superuser): redirecionado para pagina 403 estilizada (`tenants/no_access.html`) com instrucoes para contactar admin
  - Se `TenantUser` e removido durante a sessao: sessao limpa automaticamente, reavaliacao no proximo request
  - Superusers continuam a ter acesso total sem restricao de tenant
- **Ficheiro novo:** `tenants/templates/tenants/no_access.html`

#### 2. Driver.tenant isolado por empresa

- **Ficheiro:** `drivers/models.py`
- **Alteracao:** Adicionado `tenant = ForeignKey(Tenant, on_delete=CASCADE)`
- **Migracao:** `drivers/migrations/0004_driver_tenant.py`

### P1 — Isolamento de Dados nas Views

#### 3. Reports tenant-filtered

- **Ficheiro:** `reports/views.py`
- **Views alteradas:** `outflows_by_customer_report`, `deliveries_report`, `customer_account_report`, `supplier_account_report`, `balances_report`
- **Alteracao:** Todas as queries de dados agora filtram por `tenant=request.tenant`. Dropdowns de cliente/fornecedor/produto tambem filtrados.

#### 4. Audit e Activity Feed tenant-filtered

- **Ficheiro:** `audit/views.py`
- **Alteracao:** `AuditLogListView.get_queryset()` e `ActivityFeedView.get_queryset()` filtram por `tenant=request.tenant`.

#### 5. Notificacoes tenant-filtered (sem cache global)

- **Ficheiro:** `audit/templatetags/notification_tags.py`
- **Alteracao:** Todas as 5 queries de notificacao (stock baixo, sem stock, entregas pendentes, contas a receber/pagar) filtram por `tenant=request.tenant`. Cache global removido — impedia dados corretos por empresa.

#### 6. Dashboard sem cache, dados sempre dinamicos

- **Ficheiro:** `app/views.py`
- **Alteracao:** Dashboard reescrito — todas as 8 querysets filtradas por `tenant=request.tenant`. Cache removido completamente para garantir dados sempre actualizados por empresa.

#### 7. cache_utils.py eliminado

- **Ficheiro:** `app/cache_utils.py` (eliminado)
- **Motivo:** Funcao `get_dashboard_cache_key()` e `invalidate_dashboard_cache()` ja nao sao utilizadas.

#### 8. Signals limpos

- **Ficheiros:** `accounts/signals.py`, `brands/signals.py`, `customers/signals.py`, `products/signals.py`, `suppliers/signals.py`
- **Alteracao:** Removidas todas as chamadas a `invalidate_dashboard_cache()` (ja nao existe).

### P2 — Gestao de Utilizadores e Grupos

#### 9. UserUpdateView e UserDeleteView tenant-filtered

- **Ficheiro:** `users/views.py`
- **Alteracao:** `get_queryset()` filtra por `tenantuser__tenant=tenant` — utilizador so pode editar/eliminar users da sua empresa.

#### 10. Group views tenant-filtered (via users)

- **Ficheiro:** `users/views.py`
- **Alteracao:** `GroupListView`, `GroupUpdateView`, `GroupDeleteView` filtram por `user__tenantuser__tenant=tenant` — grupos visiveis apenas se tiverem utilizadores da empresa actual.

#### 11. Criacao de utilizador mostra empresa e funcao

- **Ficheiro:** `users/forms.py`, `users/views.py`, `users/templates/user_create.html`
- **Alteracao:**
  - Formulario `UserCreateForm` aceita `tenant` nos kwargs, adiciona campo `tenant_role` com choices `TenantUser.ROLE_CHOICES`
  - View `UserCreateView` passa tenant ao form, usa role selecionada ao criar `TenantUser`
  - Template exibe banner "EMPRESA" com o nome antes do formulario
- **Nota:** O criador so pode atribuir o utilizador a empresa a que pertence.

### P3 — UX/UI Profissional

#### 12. Pagina de selecao de empresa redesenhada

- **Ficheiro:** `tenants/templates/tenants/tenant_select.html`
- **Alteracao:** Cards com avatar, nome, role, badge "Principal". Empresas ordenadas por `-is_primary, tenant__name`. Secoes "EMPRESA PRINCIPAL" / "OUTRAS EMPRESAS".

#### 13. Selector de empresa no header (troca rapida)

- **Ficheiro:** `app/templates/components/_header.html`
- **Alteracao:** Badge estatico substituido por dropdown interativo:
  - Mostra nome da empresa actual
  - Dropdown com todas as empresas do utilizador
  - Empresa actual marcada com check verde
  - Troca instantanea via POST + redirect ao dashboard

#### 14. CSS para componentes tenant

- **Ficheiro:** `app/static/css/style.css`
- **Adicionado:** Estilos `.btn-tenant-card`, `.tenant-card-*`, `.tenant-switcher-btn`, `.tenant-switcher-item`, `.logo-box-lg`

### Testes

#### 15. Testes actualizados

- **Ficheiro:** `users/tests.py`
- **Alteracao:** 4 testes ajustados — utilizadores sem empresa ja nao acedem a paginas de dados empresariais (recebem 403, comportamento correcto com o novo middleware).
- **Total:** 173 testes, todos passing.

### Resumo Estatistico

| Metrica | Valor |
|---|---|
| Ficheiros criados | 22 |
| Ficheiros modificados | 40+ |
| Testes (total) | 173 |
| Testes escritos (cumulativo) | 93 |
| Apps Django | 11 |
| Migrations geradas | 6 |
| Correcoes de seguranca | 9 |
| Novas funcionalidades | 7 |
| Templates criados | 13 |
