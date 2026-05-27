# Resumo das Melhorias — SGE (Sistema de Gestao de Stocks)

**Data:** 2026-05-26
**Testes:** 174/174 passam · **Cobertura:** 87% (4969 statements, 648 missed)

---

## 1. Unificacao de Headers (Task #6)

**Problema:** 3 padroes diferentes de cabecalho de pagina espalhados pelo sistema.

**Solucao:** Todas as 9 paginas usam agora o mesmo padrao:

```html
<div class="page-header">
  <div class="page-header-title">
    <a href="{% url 'xxx_list' %}" class="btn-action me-1"><i class="bi bi-arrow-left"></i></a>
    <div><h1 class="fw-bold mb-0 fs-5">Titulo</h1><span class="text-muted small">Subtitulo</span></div>
  </div>
</div>
```

**Ficheiros alterados:**
- `payment_create.html`, `payment_update.html`, `delivery_create.html`
- `report_deliveries.html`, `customer_account.html`, `supplier_account.html`
- `home.html`, `product_list.html`, `product_detail.html`
- `app/static/css/style.css` — adicionado `.page-header-title`

---

## 2. Extracao de Scripts Inline (Task #7)

**Problema:** Scripts `<script>` inline espalhados pelos templates — duplicacao e nao funcionam com HTMX.

**Solucao:** Criados 3 ficheiros JS externos com event delegation no `document`:

| Ficheiro | Responsabilidade |
|---|---|
| `app/static/js/main.js` | HTMX loading bar, teclas de atalho, modal de delete, bulk select/delete, sidebar toggle, confirm dialogs, print trigger |
| `app/static/js/payment-form.js` | Toggle tipo de pagamento (recebimento/pagamento) |
| `app/static/js/chart-init.js` | Inicializacao do Chart.js via data attributes |

**Ficheiros alterados:**
- `app/templates/base.html` — ~45 linhas de script inline substituidas por `<script src="{% static 'js/main.js' %}">`
- `app/templates/home.html` — canvas usa `data-labels`, `data-inflows`, `data-outflows` em vez de script inline
- `payments/templates/_payment_form.html` — script inline substituido
- `app/templates/components/_delete_modal.html` — script inline removido
- `products/templates/product_list_partial.html` — script bulk select removido
- `app/views.py` — dados do grafico serializados com `json.dumps()` em vez de `|safe`

---

## 3. Seguranca: DEBUG = False por Default (Task #11)

**Problema:** `DEBUG` estava `True` por omissao em producao — risco de fuga de dados.

**Solucao:** Alterado `app/settings.py:27`:

```python
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
```

**Ajustes necessarios:**
- `tests/conftest.py` — `os.environ['DJANGO_DEBUG'] = 'True'` (force-set)
- `pytest.ini` — removido `DJANGO_SETTINGS_MODULE = app.settings` (carregava settings antes do conftest.py)

---

## 4. Remocao de Event Handlers Inline (Task #13)

**Problema:** `onsubmit="return confirm(...)"` e `onclick="window.print()"` em 15+ templates — ma pratica de CSP.

**Solucao:** Substituidos por data attributes com event delegation no `main.js`:

| Antes | Depois |
|---|---|
| `onsubmit="return confirm('...')"` | `data-confirm="..."` |
| `onclick="document.querySelector('.sge-sidebar').classList.remove('show')"` | `data-close-sidebar` |
| `onclick="window.print()"` | `class="js-print-trigger"` |

**Ficheiros alterados:**
- 10 ficheiros trash partial (brand, category, supplier, customer, product, payment, outflow, inflow, driver, delivery)
- 5 botoes de impressao (outflow_detail, delivery_shipping_guide, supplier_account, customer_account, report_deliveries)
- `app/templates/components/_sidebar.html`
- `app/static/js/main.js` — adicionados 3 novos delegated handlers

---

## 5. Optimizacao de Queries: select_related (Task #14 / #18)

**Problema:** N+1 queries em views que acediam a ForeignKeys sem `select_related`.

**Solucao:** Adicionado `get_queryset()` com `select_related`/`prefetch_related` onde faltava:

| View | Optimizacao |
|---|---|
| `InflowDetailView` | `select_related('product', 'supplier')` |
| `ProductDetailView` | `select_related('category', 'brand')` |
| `OutflowDetailView` | `select_related('product', 'customer')` + `prefetch_related('deliveries__driver')` |
| `OutflowListView` | `select_related('product', 'customer')` |
| `OutflowTrashListView` | `select_related('product', 'customer')` |
| `DeliveryShippingGuideView` | `select_related('outflow__product', 'outflow__customer', 'driver')` |
| `DeliveryTrashListView` | `select_related('outflow__product', 'outflow__customer', 'driver')` |
| `PaymentListView` | `select_related('customer', 'supplier')` |

---

## 6. Refactor de reports/views.py (Task #12)

**Problema:** 779 linhas com ~220 linhas de codigo duplicado entre extrato de clientes e fornecedores (Excel + PDF).

**Solucao:** Criado `reports/export_utils.py` com funcoes parametrizadas:

| Funcao | Descricao |
|---|---|
| `build_excel_response()` | Export Excel generico (usado por outflows, deliveries, balances) |
| `build_pdf_response()` | Export PDF generico |
| `build_account_excel()` | Extrato Excel parametrizado (`account_type='customer'` ou `'supplier'`) |
| `build_account_pdf()` | Extrato PDF parametrizado |

**Resultado:**
- `reports/views.py` — **779 → 416 linhas** (reducao de 47%)
- `reports/export_utils.py` — 293 linhas (novo)
- Logica de cor por linha, saldo corrente, e totais partilhada entre cliente e fornecedor

---

## 7. Seguranca: CSP + HSTS + Cookies Seguros (Tasks #14, #15)

**Problema:** Headers de seguranca ausentes — sem CSP, sem HSTS, cookies sem flags de seguranca.

**Solucao:**

### Content-Security-Policy (Task #15)
Novo middleware `app/middleware.py` com politica restritiva:
```
default-src 'self'
script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net
style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net
img-src 'self' data:
font-src 'self' https://cdn.jsdelivr.net
frame-ancestors 'none'
base-uri 'self'
form-action 'self'
```

### Configuracao de Producao (Task #14)
```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')          # obrigatorio via env var
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', ...) # via env var
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000     # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
```

**Ficheiros alterados:**
- `app/middleware.py` — novo ficheiro (22 linhas)
- `app/settings.py` — SECRET_KEY obrigatorio, ALLOWED_HOSTS via env, HSTS + cookies seguros

---

## 8. Base de Dados: Indices e Constraints (Task #17)

**Problema:** Falta de indices em campos de filtro/pesquisa e ausencia de constraints de integridade.

**Solucao:** Adicionados indices e constraints via migracoes:

| App | Indices / Constraints |
|---|---|
| `audit` | `(model_name, object_id)`, `(user, timestamp)` |
| `accounts` | `(customer, date)`, `(customer, outflow)`, `(supplier, date)`, `(supplier, inflow)` + CHECK constraints (credit/debit mutual exclusion) |
| `brands` | `(name,)` unique |
| `categories` | `(name,)` unique |
| `customers` | `(name,)`, `(email,)` |
| `drivers` | `(name,)`, `(phone,)` |
| `outflows` | `(product, customer)`, `(created_at,)`, `(is_deleted,)`, `(status,)` + `(outflow, driver, delivered_at)` on Delivery |
| `payments` | CHECK constraints (type + entity mutual exclusion) |
| `products` | `(category, brand)`, `(title,)` |
| `suppliers` | `(name,)`, `(email,)` |

---

## 9. Refactor de CRUD Views com Mixins Genericos (Task #16)

**Problema:** Cada app duplicava ~100 linhas de views CRUD identicas (LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, etc.).

**Solucao:** Criadas classes base em `app/mixins.py`:

| Classe Base | Heranca |
|---|---|
| `BaseListView` | LoginRequired + PermissionRequired + Htmx + Export + FilterView |
| `BaseCreateView` | LoginRequired + PermissionRequired + SuccessMessage + CreateView |
| `BaseUpdateView` | LoginRequired + PermissionRequired + SuccessMessage + UpdateView |
| `BaseDetailView` | LoginRequired + PermissionRequired + DetailView |
| `BaseDeleteView` | LoginRequired + PermissionRequired + DeleteView (com tratamento de ProtectedError) |
| `BaseTrashListView` | LoginRequired + PermissionRequired + Htmx + ListView (filtra `is_deleted=True`) |
| `BaseRestoreView` | LoginRequired + PermissionRequired + View (generico, recebe `model` + `redirect_url`) |
| `BaseHardDeleteView` | LoginRequired + PermissionRequired + View (generico, com tratamento de ProtectedError) |

**Resultado:**
- 5 apps refactoradas: `brands`, `categories`, `customers`, `suppliers`, `drivers`
- Cada app passou de ~100 linhas para ~55-80 linhas
- `app/mixins.py` — 318 linhas (inclui tambem SoftDeleteModel, SoftDeleteManager, BulkDeleteMixin, HtmxMixin, ExportMixin)

---

## 10. URL Namespaces em Todas as Apps (Task #19)

**Problema:** URLs sem `app_name` — colisoes entre apps com nomes iguais (ex: `brand_list` vs `category_list`).

**Solucao:** Adicionado `app_name` aos 13 ficheiros `urls.py`:

```python
app_name = 'brands'  # (ou 'categories', 'customers', etc.)
urlpatterns = [...]
```

**Actualizacao de referencias:**
- ~270 referencias actualizadas em 111 ficheiros:
  - Templates: `{% url 'brand_list' %}` → `{% url 'brands:brand_list' %}`
  - Python: `reverse_lazy('brand_list')` → `reverse_lazy('brands:brand_list')`
  - Python: `redirect('brand_list')` → `redirect('brands:brand_list')`

**Namespaces criados:** `brands`, `categories`, `suppliers`, `customers`, `products`, `inflows`, `outflows`, `accounts`, `payments`, `drivers`, `reports`, `users`, `audit`

---

## 11. Cobertura de Testes: 73% → 87% (Task #20)

**Problema:** Cobertura de testes baixa — apenas 73% do codigo coberto.

**Solucao:** Adicionados ~98 novos testes em 6 modulos:

| Modulo | Testes adicionados | Foco |
|---|---|---|
| `app/tests/test_dashboard.py` | 13 | Dashboard view, cache, context data, 404/500 handlers |
| `accounts/tests.py` | +12 | CustomerAccountListView, SupplierAccountListView, PaymentCreateView POST, BalanceListView, model __str__ |
| `reports/tests.py` | +20 | Filtros (customer, supplier, date, status, section), export Excel/PDF para todas as views |
| `products/tests.py` | +18 | CRUD completo + bulk delete + 404 |
| `outflows/tests.py` | +22 | CRUD completo + delivery workflow + shipping guide + confirm weight + trash/restore/hard-delete |
| `inflows/tests.py` | +13 | InflowViewTest: CRUD + trash views |

**Template criado:**
- `payments/templates/payments/_payment_form.html` — partial que estava em falta (referenciado por payment_create.html e payment_update.html)

**Resultado final:**
- 174 testes, todos passam
- Cobertura: **87%** (4969 statements, 648 missed)
- 32 ficheiros vazios skipped (migrations, __init__.py, etc.)

---

## 12. Bug Fixes

### 12.1. Namespace em reverse_lazy com kwargs
**Bug:** Script de migracao de namespaces nao processou `reverse_lazy('url_name', kwargs=...)`, apenas `reverse_lazy('url_name')`.

**Fix:** Corrigido `outflows/views.py` linhas 194 e 218:
```python
# Antes
reverse_lazy('outflow_detail', kwargs={'pk': ...})
# Depois
reverse_lazy('outflows:outflow_detail', kwargs={'pk': ...})
```

### 12.2. DeliveryConfirmWeightView — overwrite de dados
**Bug:** `form_valid()` guardava uma instancia separada (`delivery.save()`), depois `super().form_valid(form)` → `form.save()` sobre-escrevia as alteracoes com a instancia original (`self.object`).

**Fix:** Actualizar `self.object` e `form.instance` para a instancia bloqueada, e deixar `super().form_valid()` fazer o unico `save()`:
```python
def form_valid(self, form):
    actual_quantity = form.cleaned_data['actual_quantity']
    with transaction.atomic():
        delivery = models.Delivery.objects.select_for_update().get(pk=self.object.pk)
        if delivery.is_confirmed:
            form.add_error(None, "Esta entrega ja foi confirmada.")
            return self.form_invalid(form)
        self.object = delivery
        form.instance = delivery
        self.object.actual_quantity = actual_quantity
        self.object.is_confirmed = True
    return super().form_valid(form)
```

---

## Estrutura Final de Ficheiros Estaticos

```
app/static/
├── css/
│   └── style.css          # +.page-header-title
└── js/
    ├── main.js             # Event delegation: HTMX, sidebar, modals, bulk ops, print, confirm
    ├── payment-form.js     # Toggle tipo pagamento
    └── chart-init.js       # Inicializacao Chart.js
```

## Estrutura de Reports

```
reports/
├── export_utils.py         # Funcoes de export partilhadas (Excel + PDF)
├── views.py                # 416 linhas (era 779)
├── filters.py
├── mixins.py
├── base.py
├── tasks.py
└── tests.py
```

## Estrutura de Mixins (app/mixins.py)

```
app/mixins.py               # 318 linhas
├── FinanceiroRequiredMixin
├── GestorRequiredMixin
├── AdminRequiredMixin
├── HtmxMixin                # Partial rendering HTMX
├── ExportMixin              # Exportacao Excel/PDF generica
├── BaseListView             # ListView + auth + permissoes + HTMX + filtros + export
├── BaseCreateView           # CreateView + auth + permissoes + mensagem
├── BaseUpdateView           # UpdateView + auth + permissoes + mensagem
├── BaseDetailView           # DetailView + auth + permissoes
├── BaseDeleteView           # DeleteView + auth + permissoes + ProtectedError handling
├── BaseTrashListView        # ListView para lixeira (soft-deleted)
├── BaseRestoreView          # View generica para restaurar
├── BaseHardDeleteView       # View generica para eliminacao permanente
├── SoftDeleteManager        # Manager que exclui soft-deleted
├── SoftDeleteAllManager     # Manager que inclui tudo
├── SoftDeleteModel          # Modelo abstracto com soft delete
├── BulkDeleteMixin          # Validacao de permissoes no admin
└── SoftDeleteViewMixin      # Soft delete em DeleteView
```
