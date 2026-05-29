# AUDITORIA ENTERPRISE COMPLETA — SGE

## SUMÁRIO EXECUTIVO

| Score | Valor |
|-------|-------|
| **Geral** | 62/100 ⚠️ |
| **Segurança** | 55/100 🔴 |
| **Performance** | 68/100 🟡 |
| **Qualidade de Código** | 70/100 🟡 |
| **UI/UX** | 65/100 🟡 |
| **Produção** | 50/100 🔴 |
| **DevOps** | 52/100 🔴 |
| **Testes** | 60/100 🟡 |

### Total de Problemas: 127
| Severidade | Qtde |
|------------|------|
| **Crítico** | 22 |
| **Alto** | 35 |
| **Médio** | 48 |
| **Baixo** | 22 |

---

## 🔴 PROBLEMAS CRÍTICOS (22)

### 1. Segurança — IDOR + Privilege Escalation em Tenants
**Arquivos:** `tenants/views.py:84-132`, `users/forms.py:48-53`, `users/views.py:111-122`
**Problema:** Qualquer user com permissão pode adicionar/remover users de QUALQUER tenant e criar users com role `admin`.
**Impacto:** Quebra total de isolamento multi-tenant. Acesso a dados financeiros de outras empresas.
**Correção:** Verificar associação do user atual ao tenant alvo. Restringir role `admin` a admins do tenant.

### 2. Segurança — `CSRF_COOKIE_HTTPONLY = True` Bloqueia HTMX
**Arquivo:** `app/settings.py:253` (já removido)
**Problema:** JavaScript não consegue ler token CSRF → todas submissões HTMX falham em produção.
**Impacto:** Sistema 100% não-funcional em produção.

### 3. Segurança — Credenciais Hardcoded no docker-compose e .env
**Arquivo:** `docker-compose.yml:7-9,41-44`, `.env.example:15,20`
**Problema:** `POSTGRES_PASSWORD: sge_secret`, `DATABASE_URL: postgres://sge:sge_secret@...`
**Impacto:** Qualquer pessoa com acesso ao repositório tem acesso à base de dados.
**Correção:** Usar `${VAR}` sem fallback sensível. Remover `sge_secret` do `.env.example`.

### 4. Segurança — API Key em Plaintext
**Arquivo:** `tenants/models.py:126`
**Problema:** `api_key = CharField(max_length=255, blank=True)` — sem hash, sem encriptação.
**Impacto:** Se base de dados for comprometida, API keys de todos os tenants são expostas.
**Correção:** Usar `make_password()` / django-hashes ou encriptar com Fernet.

### 5. Segurança — S3 URLs Publicamente Acessíveis
**Arquivo:** `app/settings.py:235`
**Problema:** `AWS_QUERYSTRING_AUTH = False` — ficheiros no S3 são world-readable.
**Impacto:** Dados financeiros (guias de remessa, facturas) expostos publicamente.
**Correção:** Remover ou set `AWS_QUERYSTRING_AUTH = True` com `AWS_QUERYSTRING_EXPIRY`.

### 6. Segurança — CSP Permite CDN Injection
**Arquivo:** `app/middleware.py:16-17`
**Problema:** `script-src https://cdn.jsdelivr.net https://unpkg.com` whitelista CDNs inteiros. `style-src-attr 'unsafe-inline'` permite CSS inline arbitrário.
**Impacto:** Atacante pode publicar package malicioso e executar XSS no domínio.
**Correção:** Restringir a paths específicos. Usar SRI + nonce. Remover `unsafe-inline`.

### 7. Segurança — Log Injection via f-string
**Arquivo:** `app/views.py:46,51`
**Problema:** `logger.warning(f"404: {request.path}")` — user controla `request.path`.
**Impacto:** Atacante injecta entradas falsas nos logs via `%0a`.
**Correção:** Usar `logger.warning("404: %s", request.path)`.

### 8. Segurança — Redis Exposto Sem Autenticação
**Arquivo:** `docker-compose.yml:18-19`
**Problema:** Redis exposto na porta `6379` para toda a rede host, sem `requirepass`.
**Impacto:** Atacante pode ler/escrever cache (filas Celery, tokens de sessão, rate limiting counters).
**Correção:** Remover `ports` ou limitar a `127.0.0.1`. Usar `REDIS_PASSWORD`.

### 9. Segurança — Nginx Sem HTTPS
**Arquivo:** `nginx.conf`
**Problema:** Sem server block 443, sem SSL. Tráfego em plaintext.
**Impacto:** Credenciais, tokens CSRF, dados financeiros transmitidos sem encriptação.
**Correção:** Adicionar SSL com Let's Encrypt + redirecionar 80→443.

### 10. Segurança — `style-src-attr 'unsafe-inline'` no CSP
**Arquivo:** `app/middleware.py:17`
**Problema:** Permite CSS inline arbitrário, anulando nonce-based CSP.
**Impacto:** XSS via `<p style="background-image: url(javascript:...)">`.
**Correção:** Usar nonce ou classes CSS em vez de inline styles.

### 11. Segurança — Cross-Tenant via FK Object Comparison
**Arquivo:** `app/mixins.py:237`
**Problema:** `getattr(obj, self.tenant_field) != tenant` — compara FK object com request.tenant.
**Impacto:** Unauthenticated & cross-tenant data access bypass.
**Correção:** Comparar PKs: `getattr(obj, f'{self.tenant_field}_id') != getattr(tenant, 'pk', None)`.

### 12. Arquitectura — Driver Plate Unique Constraint Global
**Arquivo:** `drivers/models.py:20-29`
**Problema:** `UniqueConstraint(fields=['truck_plate'])` sem tenant scope.
**Impacto:** Duas empresas não podem registar a mesma matrícula.
**Correção:** `UniqueConstraint(fields=['tenant', 'truck_plate'])`.

### 13. Lógica — Dashboard GROUP BY name em vez de ID
**Arquivo:** `app/views.py:115-119`
**Problema:** `values('customer__name')` — dois customers com mesmo nome são agregados juntos.
**Impacto:** Totais financeiros incorrectos no dashboard.
**Correção:** Usar `customer_id` ou `customer__id`.

### 14. Lógica — Fórmula de Margem usa Markup, não Margin
**Arquivo:** `app/views.py:137`
**Problema:** `(total_sell - total_cost) / total_cost * 100` — é markup, não margin.
**Impacto:** Margem sobrestimada. Ex: custo 80, venda 100 mostra 25% (correcto: 20%).
**Correção:** `(total_sell - total_cost) / total_sell * 100`.

### 15. DevOps — Dependências de Teste em Produção
**Arquivo:** `requirements.txt:15-18`
**Problema:** `pytest`, `pytest-cov`, `coverage` instalados na imagem de produção Docker.
**Impacto:** Aumento de superfície de ataque, consumo de memória desnecessário.
**Correção:** Mover para `requirements-dev.txt`. Criar `requirements-prod.txt`.

### 16. DevOps — Nenhum Security Scan no CI
**Arquivo:** `.github/workflows/ci.yml`
**Problema:** Sem `pip-audit`, `bandit`, `trivy`, `safety`, `semgrep`.
**Impacto:** Vulnerabilidades nas dependências não são detectadas.
**Correção:** Adicionar `pip-audit`, `bandit -r .`, `trivy fs .` no pipeline.

### 17. DevOps — Redis Sem `deploy.resources.limits`
**Arquivo:** `docker-compose.yml`
**Problema:** Sem limites de CPU/memória em nenhum serviço.
**Impacto:** Um container pode consumir toda a RAM do host (OOM killer).
**Correção:** Adicionar `deploy.resources.limits.cpus: '1' memory: 512M`.

### 18. Testes — Hardcoded URLs em TODOS os testes
**Arquivo:** Todos os `tests.py` (12 ficheiros)
**Problema:** `'/brands/list/'` em vez de `reverse('brands:brand_list')`.
**Impacto:** Se URLs mudarem, testes passam mas testam endpoint errado.
**Correção:** Substituir por `reverse()` em todos os testes.

### 19. Testes — Sem Testes de Isolamento de Tenant
**Arquivo:** `products/tests.py`, `suppliers/tests.py`, `brands/tests.py`, `categories/tests.py`, `customers/tests.py`, `drivers/tests.py`, `inflows/tests.py`, `payments/tests.py`, `accounts/tests.py`
**Problema:** Zero testes cross-tenant. Fuga de dados não detectada.
**Impacto:** Qualquer bug de tenant isolation passa despercebido em CI.
**Correção:** Adicionar testes que criam tenant B e verificam que user A não vê dados de B.

### 20. Sinais — Missing `dispatch_uid` em TODOS os signals
**Arquivo:** `inflows/signals.py`, `outflows/signals.py`, `accounts/signals.py`, `payments/signals.py`, `audit/signals.py`
**Problema:** Nenhum signal usa `dispatch_uid`. Se `ready()` for chamado múltiplas vezes, handlers disparam N vezes.
**Impacto:** Duplicação de lançamentos contábeis, stock actualizado múltiplas vezes.
**Correção:** Adicionar `dispatch_uid` a todos os `@receiver` decorators.

### 21. Sinais — Race Condition em Outflow Signal
**Arquivo:** `outflows/signals.py:31-38`
**Problema:** `pending = outflow.quantity - outflow.quantity_delivered` — lê sem lock, valida, depois actualiza com `F()`. TOCTOU clássico.
**Impacto:** Em concorrência, stock pode ficar negativo ou incorreto.
**Correção:** Usar `select_for_update()` na view + signal, ou validar atomicamente com `filter().update()`.

### 22. Sinais — Pre_save no AuditLog faz DB query em cada save
**Arquivo:** `audit/signals.py:85-102`
**Problema:** Cada `save()` de modelo tracked: 1 DB query + itera todos os campos + `str()` em cada um.
**Impacto:** Adiciona ~5-10ms a cada save, mesmo sem alterações.
**Correção:** Usar `django-audit-log` ou versão optimizada que só compara dirty fields.

---

## 🟠 PROBLEMAS ALTOS (35)

### 1. Segurança — DB SSL `prefer` em vez de `require`
`app/settings.py:133` — Conexão PostgreSQL pode cair para unencrypted.

### 2. Segurança — Nginx Sem Security Headers
`nginx.conf` — Sem `X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `HSTS`, `Referrer-Policy`.

### 3. Segurança — Nginx Sem Rate Limiting
`nginx.conf` — Sem `limit_req_zone`. Ataques brute-force diretos ao Django.

### 4. Segurança — Expõe `str(e)` em Health Check
`app/views.py:29` — `{'database': str(e)}` expõe detalhes de erro da DB.

### 5. Segurança — DEBUG Auto-Detect frágil
`app/settings.py:29-36` — Se `pytest` estiver em `sys.modules` em produção, DEBUG=True.

### 6. Segurança — Rate Limiting Per-Process (LocMem)
`app/settings.py:274` — Sem Redis, rate limiting é por worker. Atacante contorna com múltiplas requests.

### 7. Segurança — JSON no Contexto da Template sem Escaping
`app/views.py:184-186` — `json.dumps()` injectado no HTML pode causar XSS.

### 8. Segurança — `task_status` Sem Tenant Scope
`reports/views.py:438-450` — Qualquer task ID de qualquer tenant pode ser consultada.

### 9. Segurança — N+1 nos Métodos de Export
`app/mixins.py:89-97` — Dot-traversal `getattr(value, attr)` sem `select_related()` → N+1 por célula.

### 10. Segurança — Restaurar/HardDelete Sem `select_for_update()`
`app/mixins.py:231-264`, todas as views de restore/hard-delete — Race conditions em stock.

### 11. Segurança — GestorRequiredMixin Permissões Trocadas
`app/mixins.py:27-34` — `ProductCreateView` requer `change_product`, `UpdateView` requer `add_product`.

### 12. Arquitectura — Missing `(tenant, is_deleted)` Index em TODOS modelos
Todos os `SoftDeleteModel` — `objects` faz `filter(is_deleted=False)` sem composite index.

### 13. Arquitectura — Missing `(tenant, created_at)` Index
`inflows/models.py`, `outflows/models.py`, `payments/models.py` — Reports sem composite index.

### 14. Arquitectura — Missing `(tenant, status)` Index em Outflow
`outflows/models.py` — Dashboard filtra por status frequentemente.

### 15. Arquitectura — Missing `(tenant, action, timestamp)` em AuditLog
`audit/models.py` — Consultas de auditoria sem index adequado.

### 16. Arquitectura — AccountEntry Não é SoftDeletable
`accounts/models.py:10-71` — Dados financeiros são permanentemente deletados.

### 17. Arquitectura — Missing `(tenant, type)` Index em Payment
`payments/models.py` — Agrupamentos por tipo sem index.

### 18. Arquitectura — UUID Primary Key Performance
`tenants/models.py:10` — UUID PK causa fragmentação em B-tree. 50+ FKs.

### 19. UI/UX — No SRI (Subresource Integrity) em CDN
`base.html:27,29,81,82`, `home.html:227`, `login.html:13,14`, `404.html:11,12` — Bootstrap, HTMX, Chart.js.

### 20. UI/UX — `|safe` em data-attributes (XSS)
`home.html:89` — `{{ month_labels|safe }}` injectado em `data-labels`.

### 21. UI/UX — `data-delete-message` Attribute Injection
Múltiplas list partials — Nome do objecto injectado sem escaping em atributo HTML.

### 22. UI/UX — Missing Loading Indicators no HTMX
Todas as listas — `hx-indicator` ausente. User não vê feedback durante requests.

### 23. UI/UX — Hardcoded 2026 no Footer
`_footer.html:8` — `© 2026` em vez de `{% now "Y" %}`.

### 24. UI/UX — Hardcoded URL em 500.html
`500.html:16` — `href="/"` em vez de `{% url 'dashboard' %}`.

### 25. UI/UX — Missing `autocomplete` em Login
`registration/login.html:89,96` — Username sem `autocomplete="username"`.

### 26. UI/UX — Trash Templates Design Inconsistente
Todos os `*_trash.html` — Usam padrão antigo, diferente do design system principal.

### 27. Testes — Missing Permission Enforcement Tests
`products/tests.py`, `inflows/tests.py`, `outflows/tests.py`, `payments/tests.py` — Zero testes de permissão.

### 28. Testes — Missing Signal Tests para Accounts/Stock
`accounts/signals.py`, `payments/signals.py` — Zero testes diretos.

### 29. Testes — Factories Não Utilizadas
Todos os testes — `tests/factories.py` existe mas testes criam objects manualmente.

### 30. Testes — Sem Testes de Concorrência
Nenhum — `select_for_update()` em paths críticos nunca testado sob race conditions.

### 31. DevOps — Sem `dependabot.yml`
Repositório — Dependências vulneráveis não são automaticamente actualizadas.

### 32. DevOps — Sem Docker Build no CI
`.github/workflows/ci.yml` — Imagem Docker não é construída nem scaneada.

### 33. DevOps — Sem Graceful Shutdown no Gunicorn
`Dockerfile:27` — Sem `--graceful-timeout`, workers podem ser mortos em meio a request.

### 34. DevOps — Pre-commit sem bandit/mypy/pip-audit
`.pre-commit-config.yaml` — 3 hooks de segurança essenciais ausentes.

### 35. DevOps — Sem Healthcheck no Dockerfile
`Dockerfile` — Sem `HEALTHCHECK`. Orquestrador não sabe se app está viva.

---

## 🟡 PROBLEMAS MÉDIOS (48)

| # | Categoria | Problema | Localização |
|---|-----------|----------|-------------|
| 1 | Código | DATABASE_URL regex falha com `@` ou `:` na password | `app/settings.py:120-137` |
| 2 | Código | Redis cache sem timeout config | `app/settings.py:151-159` |
| 3 | Código | `hasattr` frágil em `TenantFilterMixin` | `app/mixins.py:167-175` |
| 4 | Código | `rate_limit` class attr nunca usado | `app/mixins.py:251-252` |
| 5 | Código | `Q` e `render_to_string` importados não usados | `app/mixins.py:5,8` |
| 6 | Código | Import dentro de função em validators | `app/validators.py:43-46` |
| 7 | Código | Validação NIF aceita vazio silenciosamente | `app/validators.py:21` |
| 8 | Código | Breadcrumbs inconsistente (login=/accounts/ = Contas) | `app/context_processors.py:29` |
| 9 | Código | Dashboard cobre 5 meses, não 6 (150 dias) | `app/views.py:139` |
| 10 | Código | 17+ queries por dashboard load, sem cache | `app/views.py:57-137` |
| 11 | Código | Missing CSP `object-src 'none'` | `app/middleware.py:14-23` |
| 12 | Código | CSP em respostas não-HTML | `app/middleware.py` |
| 13 | Código | `manage.py health_check` não existe | `app/views.py:25` |
| 14 | DB | Produto serial_number unique não scoped | `products/models.py:34-38` |
| 15 | DB | Customer phone sem index | `customers/models.py:10` |
| 16 | DB | Driver missing plate indexes | `drivers/models.py` |
| 17 | DB | Delivery `delivered_at` auto_now_add | `outflows/models.py:145` |
| 18 | DB | Delivery sem `updated_at` | `outflows/models.py` |
| 19 | DB | `deleted_at` sem db_index | `app/mixins.py:279` |
| 20 | DB | Missing `(tenant, role)` em TenantUser | `tenants/models.py:53-74` |
| 21 | DB | N+1 em admin de Inflow/Delivery/Payment | Admin files |
| 22 | DB | `null=True, blank=True` inconsistente | Múltiplos modelos |
| 23 | Segurança | Missing rate limiting em write endpoints | CRUD views (15+) |
| 24 | Segurança | `InflowUpdateView` sem `select_for_update()` | `inflows/views.py:72-91` |
| 25 | Segurança | `OutflowUpdateView` save fora do atomic block | `outflows/views.py:101-123` |
| 26 | Segurança | Password strength validation ausente | `users/forms.py:40-81` |
| 27 | Segurança | Tenant switch sem re-autenticação | `tenants/views.py:21-28` |
| 28 | Segurança | Negative price permitido em forms | `inflows/forms.py:9`, `outflows/forms.py:9` |
| 29 | Segurança | `pre_delete` overlap em accounts signals | `accounts/signals.py` |
| 30 | Segurança | Inflow signals sem transaction.atomic() | `inflows/signals.py` |
| 31 | Segurança | `update_or_create` sem try/except em accounts | `accounts/signals.py` |
| 32 | UI/UX | N+1 em user_list.html `u.groups.all` | `user_list.html:23` |
| 33 | UI/UX | Missing `aria-label` em icon-only buttons | Múltiplos templates |
| 34 | UI/UX | Missing `loading="lazy"` em imagens | `user_profile.html:166` |
| 35 | UI/UX | Export link sem `|urlencode` | `product_list.html:11-12` |
| 36 | UI/UX | `payment_detail.html` sem `floatformat` | `payment_detail.html:30` |
| 37 | UI/UX | Missing `scope="col"` em table headers | Todos os list partials |
| 38 | UI/UX | Form dentro de form (report_balances) | `report_balances.html:24` |
| 39 | UI/UX | `window.fetch` override em csrf.js | `csrf.js:29-40` |
| 40 | Testes | `pytest.ini` --cov inclui packages instalados | `pytest.ini:5` |
| 41 | Testes | `app` em testpaths sem testes | `pytest.ini:6` |
| 42 | Testes | Missing export tests (non-report) | products, suppliers tests |
| 43 | Sinais | TOCTOU em delivery pre_save | `outflows/signals.py:8-18` |
| 44 | Sinais | Audit signals weak=False sem dispatch_uid | `audit/signals.py:63-109` |
| 45 | DevOps | Sem logs estruturados no gunicorn | `Dockerfile:27` |
| 46 | DevOps | Sem `--max-requests` no gunicorn | `Dockerfile:27` |
| 47 | DevOps | Sem `task_acks_late` no Celery | App config |
| 48 | DevOps | `.env.example` versionado com placeholders | `.env.example` |

---

## 🟢 PROBLEMAS BAIXOS (22)

| # | Categoria | Problema | Localização |
|---|-----------|----------|-------------|
| 1 | Código | Mix português/inglês em URLs/comentários | Múltiplos |
| 2 | Código | Version '1.0.0' hardcoded em 2 lugares | `app/views.py:41`, `settings.py:257` |
| 3 | Código | HSTS 1 ano sem ramp-up | `app/settings.py:250-251` |
| 4 | Código | `BACKUP_DIR.mkdir()` sem mode explícito | `app/settings.py:261` |
| 5 | Código | `SECURE_SSL_REDIRECT` pode causar loop atrás de nginx | `app/settings.py:252` |
| 6 | Código | `__init__.py` exclude do flake8 | `setup.cfg:4` |
| 7 | Código | Sem mypy/pyright/djangonaut config | `setup.cfg` |
| 8 | Código | `static()` helper com AWS S3 config | `app/urls.py:32-33` |
| 9 | Código | Logger criado em método (não módulo) | `app/mixins.py:303` |
| 10 | DB | Inflow price nullable sem default | `inflows/models.py:18` |
| 11 | DB | TenantSettings `auto_approve_below_amount` max_digits=10 inconsistente | `tenants/models.py:108-110` |
| 12 | DB | Redundant individual db_index quando composite index já cobre | Supplier/Customer nif, email |
| 13 | UI/UX | Missing `scope="col"` em table headers | Todos os list partials |
| 14 | UI/UX | `password_change_form` hardcoded input | `password_change_form.html:9` |
| 15 | UI/UX | `_notifications.html` sem `|escape` em href | `_notifications.html:11-16` |
| 16 | UI/UX | `_breadcrumbs.html` sem `|escape` em href | `_breadcrumbs.html:7` |
| 17 | Testes | conftest.py tem test secret key | `conftest.py:5` |
| 18 | Testes | tests/__init__.py vazio | `tests/__init__.py` |
| 19 | DevOps | `*.log` não ignorado pelo git | `.gitignore` |
| 20 | DevOps | `.DS_Store` não ignorado | `.gitignore` |
| 21 | DevOps | Sem `requirements-txt-fixer` no pre-commit | `.pre-commit-config.yaml` |
| 22 | DevOps | `flower` em dev reqs mas celery inconsistente | `requirements-dev.txt:7` |

---

## PLANO DE CORRECÇÃO PRIORITÁRIO

### ✅ FASE 1 — CRÍTICAS (CONCLUÍDA)
Ações que bloqueiam a segurança básica e funcionalidade do sistema.

| Prioridade | Tarefa | Esforço | Status |
|------------|--------|---------|--------|
| P0 | Fix IDOR + PrivEsc em tenants/views.py | 4h | ✅ |
| P0 | Remover hardcoded secrets do docker-compose + .env.example | 1h | ✅ |
| P0 | Fix CSP: CDN whitelist + unsafe-inline | 2h | ✅ |
| P0 | Adicionar SSL/HTTPS no nginx | 3h | ✅ |
| P0 | Fix rate limiting per-process (forçar Redis) | 2h | ✅ |
| P0 | API key hashing (tenants/models.py) | 1h | ✅ |
| P0 | Adicionar dispatch_uid em todos os signals | 2h | ✅ |
| P0 | Fix race condition em outflow signal | 4h | ✅ |
| P0 | Adicionar (tenant, is_deleted) index em todos modelos | 3h | ✅ |
| P0 | Remover pytest de requirements de produção | 1h | ✅ |

**Ficheiros alterados na Fase 1:**
- `tenants/views.py` — IDOR fix + membership checks + PermissionDenied
- `tenants/forms.py` — Role restriction for non-admin users
- `tenants/models.py` — API key hashing + set/check methods
- `users/forms.py` — Role restriction on user creation
- `users/views.py` — Pass request to form kwargs
- `app/middleware.py` — CSP restrito a paths específicos, sem unsafe-inline, object-src 'none', não-HTML skip
- `app/settings.py` — Redis connection pool + LocMemCache warning + DB SSL 'require'
- `nginx.conf` — HTTPS + SSL config + rate limiting + security headers
- `Dockerfile` — Non-root user + HEALTHCHECK + graceful shutdown + max-requests + prod requirements
- `requirements.txt` — Agora include `requirements-prod.txt` + dev/test deps
- `requirements-prod.txt` — NOVO: apenas deps de produção (sem pytest)
- `inflows/signals.py` — dispatch_uid adicionado
- `outflows/signals.py` — dispatch_uid + select_for_update fix race condition
- `accounts/signals.py` — dispatch_uid adicionado
- `payments/signals.py` — dispatch_uid adicionado
- `audit/signals.py` — dispatch_uid adicionado
- `products/models.py` — Index (tenant, is_deleted)
- `brands/models.py` — Index (tenant, is_deleted)
- `categories/models.py` — Index (tenant, is_deleted)
- `suppliers/models.py` — Index (tenant, is_deleted)
- `customers/models.py` — Index (tenant, is_deleted)
- `drivers/models.py` — Index (tenant, is_deleted) + tenant-scoped unique constraints
- `inflows/models.py` — Index (tenant, is_deleted)
- `outflows/models.py` — Index (tenant, is_deleted) em Outflow e Delivery
- `payments/models.py` — Index (tenant, is_deleted)

### FASE 2 — ALTAS (Semana 2)
Proteção de dados, performance, e qualidade.

| Prioridade | Tarefa | Esforço |
|------------|--------|---------|
| P1 | Cross-tenant FK comparison fix (mixins.py) | 2h |
| P1 | DB SSL `require` | 1h |
| P1 | Security headers no nginx | 2h |
| P1 | Nginx rate limiting | 1h |
| P1 | Fix GROUP BY name no dashboard | 1h |
| P1 | Fix margin formula | 1h |
| P1 | Adicionar SRI em CDN resources | 2h |
| P1 | Security scan no CI (pip-audit, bandit) | 4h |
| P1 | Adicionar dependabot.yml | 1h |
| P1 | Adicionar `select_for_update()` em restore/hard-delete | 4h |
| P1 | Adicionar tenant isolation tests | 8h |
| P1 | Adicionar permission enforcement tests | 8h |

### FASE 3 — MÉDIAS (Semanas 3-4)
Refinamento, observabilidade, e UX.

| Prioridade | Tarefa | Esforço |
|------------|--------|---------|
| P2 | Composite indexes restantes | 3h |
| P2 | Rate limiting em write endpoints | 4h |
| P2 | Loading indicators HTMX | 4h |
| P2 | Dashboard caching | 8h |
| P2 | Healthcheck endpoint | 2h |
| P2 | Gunicorn graceful shutdown + max-requests | 2h |
| P2 | Negative price validation | 1h |
| P2 | `deleted_at` db_index | 1h |
| P2 | User password validation | 2h |
| P2 | `|safe` removal nos templates | 3h |
| P2 | Refatorar testes para usar reverse() | 4h |
| P2 | Refatorar testes para usar factories | 8h |

### FASE 4 — BAIXAS (Semanas 4-5)
Polimento final.

| Prioridade | Tarefa | Esforço |
|------------|--------|---------|
| P3 | Cleanup imports não usados | 2h |
| P3 | `null=True, blank=True` consistency | 2h |
| P3 | Hardcoded version → settings.APP_VERSION | 1h |
| P3 | Responsividade mobile (testar) | 4h |
| P3 | aria-label em icon-only buttons | 2h |
| P3 | gitignore gaps | 0.5h |
| P3 | mypy/pyright config | 2h |
| P3 | Breadcrumbs login fix | 0.5h |

---

## CHECKLIST PRODUCTION-READY

- [ ] **HTTPS** configurado no nginx
- [ ] **SSL** no PostgreSQL (sslmode=require)
- [ ] **Secrets** removidos do código (usar env vars)
- [ ] **CSP** configurado correctamente (sem unsafe-inline, sem CDN whitelist amplo)
- [ ] **SRI** em todos os CDN resources
- [ ] **Rate limiting** funcional (Redis + nginx)
- [ ] **IDOR** eliminado em todas as views
- [ ] **Isolamento multi-tenant** verificado (testes de cross-tenant)
- [ ] **Stock tracking** verificado (signals, race conditions)
- [ ] **Healthcheck** endpoint implementado
- [ ] **Graceful shutdown** (gunicorn --graceful-timeout)
- [ ] **max-requests** no gunicorn (memory leak prevention)
- [ ] **Non-root user** no Docker
- [ ] **Resource limits** no docker-compose
- [ ] **Dependabot** configurado
- [ ] **Security scan** no CI
- [ ] **Logs estruturados** (gunicorn access log, formato JSON)
- [ ] **Backup automático** configurado
- [ ] **Monitoramento** (Sentry + métricas)
- [ ] **`manage.py check --deploy`** sem warnings

## CHECKLIST OWASP TOP 10

| # | Categoria | Status |
|---|-----------|--------|
| A01 | Broken Access Control | ⚠️ IDOR em tenants. Sem tenant isolation tests |
| A02 | Cryptographic Failures | ⚠️ API key plaintext. DB SSL `prefer` |
| A03 | Injection | ✅ Django ORM. ⚠️ Log injection via f-string |
| A04 | Insecure Design | ⚠️ Race conditions em signals. Margem financeira errada |
| A05 | Security Misconfiguration | 🔴 CSP fraco. HTTPS ausente. Redis exposto |
| A06 | Vulnerable Components | ⚠️ Dependências pinned sem range. Sem security scan |
| A07 | Authentication Failures | ⚠️ Missing rate limiting. Password sem validação |
| A08 | Integrity Failures | ⚠️ S3 sem auth. NuGet/CDN sem SRI |
| A09 | Logging & Monitoring | ⚠️ Log injection. Sem métricas. Sentry mal config |
| A10 | SSRF | ✅ Não identificado |

## CHECKLIST DEVOPS

- [ ] Dockerfile multi-stage optimizado
- [ ] Non-root user no container
- [ ] Resource limits em todos os serviços
- [ ] Network isolation (backend/frontend networks)
- [ ] Healthchecks em todos os serviços
- [ ] Log driver configurado (json-file com rotação)
- [ ] Secrets management (Docker secrets ou .env não versionado)
- [ ] CI/CD com security scanning
- [ ] Dependabot configurado
- [ ] Pre-commit com hooks de segurança

## CHECKLIST ESCALABILIDADE

- [ ] Composite indexes em todas queries frequentes
- [ ] Dashboard queries com cache (Redis)
- [ ] Export assíncrono via Celery (>1000 registos)
- [ ] Paginação em todas as listas
- [ ] `select_related`/`prefetch_related` em todas as queries
- [ ] `iterator()` em export tasks
- [ ] Connection pool no Redis
- [ ] UUID PK → considerar BigAutoField
- [ ] `task_acks_late` no Celery
- [ ] `--max-requests` no gunicorn

## RECOMENDAÇÕES DE ARQUITECTURA ENTERPRISE

### 1. Service Layer Pattern
Actualmente, lógica de negócio está espalhada entre views, signals, e models. Criar camada de serviços:
```
services/
├── inflow_service.py    # Stock + supplier account sync
├── outflow_service.py   # Stock validation + delivery sync
├── payment_service.py   # Account reconciliation
└── report_service.py    # Aggregated queries + caching
```

### 2. Repository Pattern para Queries Complexas
Para queries de dashboard e relatórios:
```python
class DashboardRepository:
    def get_monthly_totals(self, tenant, months=6):
        # Centraliza queries + cache
```

### 3. Cache Layer Estratégico
- Cache dashboard metrics (invalida a cada hora ou por evento)
- Cache listagens de lookup (suppliers, products, customers)
- Cache resultados de relatórios (TTL baseado em frequência)

### 4. Event-Driven para Acções Cross-App
Substituir signals frágeis por event bus:
```python
class StockEventBus:
    def on_inflow_created(self, inflow):
        self.publish('stock.increased', product_id=inflow.product_id, quantity=inflow.quantity)
```

### 5. API Versioning
Se houver planos de expor API externa, versionar desde já:
```
/api/v1/products/
/api/v2/outflows/
```

### 6. Observabilidade
- `django-prometheus` para métricas de requests, DB, cache
- `opentelemetry` para tracing distribuído
- `structlog` para logs estruturados JSON
- Dashboards Grafana para visibilidade operacional

---

*Auditoria realizada em 29 de Maio de 2026*
*Total de 127 problemas identificados: 22 críticos, 35 altos, 48 médios, 22 baixos*
*Score geral: 62/100 — Necessita intervenção antes de produção enterprise*
