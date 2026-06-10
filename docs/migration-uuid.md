# Plano de Migração: UUID → BigAutoField no Model Tenant

## Problema
O model `Tenant` usa `UUIDField(primary_key=True)`, o que degrada performance em:
- **Joins**: UUID (128-bit) é mais lento que BigInt (64-bit) em índices
- **Índices clustered**: PostgreSQL lida melhor com sequences monotônicas
- **Armazenamento**: UUID ocupa mais espaço que BigInt em FK indexes

## Escopo do Impacto

### Foreign Keys diretas para Tenant:
| App | Model | Campo |
|-----|-------|-------|
| tenants | TenantUser | tenant (FK) |
| tenants | TenantSettings | tenant (OneToOne) |
| todos os outros | — | tenant (FK) em cada model |

### Referências indiretas (código):
- `app/mixins.py` — TenantModelFormMixin usa `tenant_id`
- `app/consumers.py` — WebSocket group usa `tenant_id`
- `app/notifications.py` — `notify_tenant(tenant_id, ...)`
- `tenants/middleware.py` — Lê `tenant_id` da session
- `tenants/views.py` — Views de seleção e switch
- `reports/export_tasks.py` — Filtra por `tenant_id`
- `reports/views.py` — Passa `tenant_id` para tasks
- `portal/views.py` — Acessa `customer.tenant_id`
- ~12 apps com `.filter(tenant=tenant)` ou `.filter(tenant_id=...)`

## Passos da Migração

### Fase 4.1 — Preparação (1 dia)
1. **Backup completo** do banco:
   ```bash
   python manage.py dumpdata --natural-primary --natural-foreign > backup_pre_migration.json
   pg_dump -U sge sge > backup_pre_migration.sql
   ```
2. **Criar branch**: `git checkout -b security/migration-uuid-bigint`
3. **Ambiente staging**: Provisionar DB clone para testes

### Fase 4.2 — Alterações no Modelo (2-3 horas)

1. **Atualizar `tenants/models.py`**:
   ```python
   class Tenant(SoftDeleteModel):
       uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
       id = models.BigAutoField(primary_key=True)
       # ... resto dos campos
   ```

2. **Criar migrações**:
   - Migração 1: Adicionar campo `uuid` (UUID, unique, nullable temporarily)
   - Migração 2: Preencher `uuid` com valores do antigo `id`
   - Migração 3: Criar novo `id` BigAutoField
   - Migração 4: Remover antigo `id` UUID
   - Migração 5: Atualizar todas as FKs

3. **Comando de dados customizado**:
   ```python
   from tenants.models import Tenant
   for t in Tenant.objects.all():
       t.uuid = t.id  # copia UUID antigo para novo campo
       t.save(update_fields=['uuid'])
   ```

### Fase 4.3 — Atualizar Código (4-6 horas)

1. **Referências a `tenant.id`**:
   - `app/mixins.py:172,175-176` — `tenant_id = tenant.id` → `tenant.id` (BigAutoField, continua igual)
   - `tenants/middleware.py:25,28` — Armazena `tenant_id` na session (agora int, não uuid)
   - `tenants/views.py` — URLs com `<uuid:tenant_id>` → `<int:tenant_id>` e `<int:pk>`
   - `tenants/urls.py:8` — Mudar regex de `uuid` para `int`
   - `app/routing.py:6` — WebSocket path regex de `[\w-]+` para `\d+`
   - `app/consumers.py:14` — `tenant_id` agora é int
   - `app/notifications.py` — `tenant_id` int

2. **Queries que filtram por UUID**:
   - `products/forms.py:56-58` — `tenant_id=int` continua funcionando
   - `outflows/signals.py` — cache key `f'dashboard_{tenant_id}'` continua igual

3. **Referências em templates**:
   - `app/templates/components/_header.html` — `tu.tenant.id` (BigAutoField) continua funcionando
   - `tenants/templates/tenants/tenant_select.html` — `value="{{ tu.tenant.id }}"` continua funcionando

### Fase 4.4 — Testes (1 dia)

1. **Testes de unidade**: Rodar `python manage.py test` — verificar que todos passam
2. **Testes de integração**: Verificar fluxo completo de tenant switching
3. **Testes de performance**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM tenants_tenant WHERE id = 1;  -- vs UUID
   EXPLAIN ANALYZE SELECT * FROM products_product WHERE tenant_id = 1;  -- vs UUID FK
   ```
4. **Testes de migração**: Verificar reversibilidade

### Fase 4.5 — Deploy (2-3 horas, requer downtime)

1. **Janela de manutenção** (mínimo 2 horas):
   - Colocar app em modo manutenção (nginx retorna 503)
   - Parar workers Celery
   - Fazer backup final
   - Rodar migrações
   - Verificar integridade dos dados
   - Reiniciar serviços
   - Remover modo manutenção

2. **Rollback plan** (se algo falhar):
   ```bash
   git checkout main
   pg_restore -U sge -d sge backup_pre_migration.sql
   ```
   Ou via Django:
   ```bash
   python manage.py migrate tenants 0001_previous
   python manage.py loaddata backup_pre_migration.json
   ```

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:------------:|:-------:|-----------|
| Perda de dados | Baixa | Crítico | Backup full antes + staging test |
| FKs quebradas | Média | Alto | Testar em staging com dados reais |
| Downtime prolongado | Média | Alto | Script de migração otimizado, janela de 4h |
| URLs/bookmarks com UUID quebram | Alta | Médio | Manter `uuid` campo acessível para lookup |

## FAQ

**P: Precisamos atualizar todas as FKs manualmente?**
R: Django gera migrações automáticas para FKs quando o tipo do PK muda. Mas é crítico verificar cada FK manualmente.

**P: O que acontece com dados existentes?**
R: O UUID antigo é preservado no campo `uuid`. O novo `id` (BigAutoField) é auto-gerado mantendo a ordem de criação.

**P: URLs de API que usam UUID vão quebrar?**
R: Sim. URLs como `/selecionar/<uuid:tenant_id>/` precisam mudar para `/selecionar/<int:tenant_id>/`.

**P: Quanto tempo de downtime?**
R: Estimado 1-2 horas para migração + verificação, dependendo do volume de dados.

**P: Vale a pena?**
R: +0.5 pontos no score de segurança/performance. Ganho de performance em joins é significativo apenas em escala (>100k tenants). Para o tamanho atual do projeto, o ganho prático é marginal.
