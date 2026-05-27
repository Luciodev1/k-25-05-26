--- PLANO_MELHORIAS_DETALHADO.md (原始)


+++ PLANO_MELHORIAS_DETALHADO.md (修改后)
# Plano Detalhado de Melhorias - SGE

**Data:** 2026-05-27
**Status do Projeto:** 29 tarefas P0-P3 concluídas, 423 testes, 94% cobertura
**Objetivo:** Implementar melhorias adicionais de segurança, arquitetura, DevOps e UX

---

## Sumário Executivo

O sistema SGE já possui uma base sólida com:
- ✅ Infraestrutura completa (Redis, Celery, Sentry)
- ✅ Validações robustas (NIF angolano, magic bytes, quantidades)
- ✅ Controlo de concorrência e transações atómicas
- ✅ Cache com invalidação automática
- ✅ Rate limiting e proteção CSRF
- ✅ Soft delete para deliveries
- ✅ exports paginados via Celery
- ✅ Suite de testes abrangente (423 testes, 94% cobertura)

**Foco deste plano:** Melhorias evolutivas em 7 áreas prioritárias

---

## 1. SEGURANÇA (Prioridade: ALTA)

### 1.1 Content-Security-Policy (CSP)
**Problema:** `'unsafe-inline'` no CSP permite XSS se atacante injetar scripts

**Implementação:**
```
Fase 1: Preparação (Dia 1-2)
  - Adicionar django-csp ao requirements.txt
  - Configurar CSP_REPORT_ONLY mode inicialmente
  - Identificar todos os inline scripts nas templates

Fase 2: Nonce Implementation (Dia 3-4)
  - Criar context processor para gerar nonce por request
  - Atualizar base.html para usar nonce em scripts
  - Testar todas as funcionalidades com CSP ativo

Fase 3: Hash para Scripts Críticos (Dia 5)
  - Gerar hashes para scripts estáticos críticos
  - Remover 'unsafe-inline' gradualmente
  - Monitorar CSP reports no Sentry

Fase 4: Produção (Dia 6)
  - Switch de CSP_REPORT_ONLY para CSP_ENFORCE
  - Documentar procedimento para novos scripts
```

**Arquivos afetados:**
- `requirements.txt`
- `app/settings.py`
- `app/context_processors.py`
- `app/templates/base.html`
- Todas as templates com scripts inline

**Critérios de Aceite:**
- [ ] CSP header presente em todas as respostas
- [ ] Zero violações CSP em produção por 7 dias
- [ ] Todos os scripts funcionais com nonce/hash
- [ ] Documentação atualizada

**Riscos:** Scripts legados podem quebrar. Mitigação: Fase de report-only.

---

### 1.2 Rate Limiting Avançado
**Problema:** Rate limit atual é apenas para login. Outras endpoints vulneráveis.

**Implementação:**
```
Fase 1: Inventory (Dia 1)
  - Listar todas as views que modificam dados
  - Identificar endpoints críticos (criação, update, delete)
  - Classificar por risco (alto/médio/baixo)

Fase 2: Middleware Global (Dia 2-3)
  - Criar app/middleware/ratelimit.py
  - Implementar rate limiting baseado em:
    * IP para endpoints anônimos
    * User ID para endpoints autenticados
  - Configurar limites diferenciados por tipo de operação

Fase 3: Endpoints Críticos (Dia 4-5)
  - Bulk delete: 10 requests/min
  - Exportações: 5 requests/min
  - Criação de registos: 30 requests/min
  - Login: Manter 5/15min + cooldown 30min (já implementado)

Fase 4: Monitoramento (Dia 6)
  - Log de violações no Sentry
  - Dashboard de rate limit violations
  - Alertas para picos anormais
```

**Arquivos afetados:**
- `app/middleware/ratelimit.py` (novo)
- `app/settings.py`
- `audit/models.py` (log de violações)
- Views críticas (decorators adicionais)

**Critérios de Aceite:**
- [ ] Todas as views listadas têm rate limiting apropriado
- [ ] Logs de violações capturados no audit trail
- [ ] Testes de carga validam limites
- [ ] Documentação de limites por endpoint

---

### 1.3 Validação Avançada de Uploads
**Problema:** Validação atual verifica magic bytes, mas não scan de malware

**Implementação:**
```
Fase 1: Validação de Tamanho e Tipo (Dia 1)
  - Adicionar limite máximo por tipo de ficheiro
  - Validar extensão vs magic bytes consistency
  - Rejeitar ficheiros com metadados suspeitos

Fase 2: Integração ClamAV (Dia 2-3)
  - Adicionar python-clamav ao requirements
  - Criar validator validate_file_malware
  - Configurar daemon ClamAV no servidor

Fase 3: Quarantine (Dia 4)
  - Criar área de quarentena para ficheiros suspeitos
  - Notificar admin via email/Celery task
  - Log detalhado no audit trail
```

**Arquivos afetados:**
- `app/validators.py`
- `requirements.txt`
- `app/settings.py` (configurações ClamAV)
- ` DeliveryForm`, outros forms com upload

**Critérios de Aceite:**
- [ ] Ficheiros >10MB rejeitados automaticamente
- [ ] Scan malware em todos os uploads
- [ ] Quarantine funcional com notificações
- [ ] Testes com samples de ficheiros maliciosos

---

## 2. ARQUITETURA E CÓDIGO (Prioridade: MÉDIA)

### 2.1 Service Layer
**Problema:** Lógica de negócio espalhada em views e models

**Implementação:**
```
Fase 1: Design (Dia 1-2)
  - Definir estrutura da service layer
  - Identificar serviços candidatos:
    * StockService (movimentações de stock)
    * AccountService (gestão de contas)
    * ReportService (geração de relatórios)
    * PaymentService (processamento de pagamentos)

Fase 2: StockService (Dia 3-5)
  - Criar app/services/stock.py
  - Mover lógica de:
    * Outflow.create() + stock update
    * Delivery.confirm() + stock adjustment
    * Inflow.create() + stock increase
  - Manter backward compatibility com models

Fase 3: AccountService (Dia 6-8)
  - Criar app/services/account.py
  - Centralizar reconciliação de contas
  - Unificar lógica Customer/Supplier accounts

Fase 4: Refatoração Progressiva (Dia 9-10)
  - Atualizar views para usar services
  - Manter tests passing durante refatoração
  - Documentar padrões de uso
```

**Arquivos afetados:**
- `app/services/` (novo diretório)
- `outflows/views.py`, `inflows/views.py`
- `accounts/views.py`
- `payments/views.py`

**Critérios de Aceite:**
- [ ] 4 serviços principais implementados
- [ ] Views usam services (não lógica direta nos models)
- [ ] Todos os testes passam após refatoração
- [ ] Documentação de API dos serviços

---

### 2.2 API RESTful (Opcional/Futuro)
**Problema:** Sistema só tem interface web, sem API para integrações

**Implementação:**
```
Fase 1: Avaliação (Dia 1-2)
  - Documentar casos de uso para API
  - Decidir: Django REST Framework ou API nativa Django
  - Priorizar endpoints críticos

Fase 2: Setup DRF (Dia 3-4)
  - Adicionar djangorestframework ao requirements
  - Configurar authentication (Token + Session)
  - Criar serializers básicos

Fase 3: Endpoints MVP (Dia 5-10)
  - GET /api/products/ (listar produtos)
  - GET /api/stock/ (stock atual)
  - POST /api/outflows/ (criar saída)
  - GET /api/reports/stock/ (relatório stock)

Fase 4: Documentação (Dia 11-12)
  - Swagger/OpenAPI docs
  - Postman collection
  - Guide de integração
```

**Nota:** Esta tarefa deve ser avaliada quanto à necessidade real. Só implementar se houver demanda de integração.

---

### 2.3 Monitoramento de Tarefas Celery
**Problema:** Tasks assíncronas sem monitoramento adequado

**Implementação:**
```
Fase 1: Flower Setup (Dia 1)
  - Adicionar flower ao requirements
  - Configurar Flower no docker-compose (se aplicável)
  - Proteger com authentication

Fase 2: Retry com Backoff (Dia 2-3)
  - Implementar exponential backoff para tasks falhadas
  - Configurar max_retries por tipo de task
  - Adicionar logging de retries

Fase 3: Alertas (Dia 4)
  - Monitorar fila de tasks falhadas
  - Alerta se >10 tasks falhadas em 1 hora
  - Integration com Sentry para errors
```

**Arquivos afetados:**
- `requirements.txt`
- `app/celery.py`
- `app/tasks.py`
- `reports/tasks.py`

---

## 3. TESTES E QUALIDADE (Prioridade: ALTA)

### 3.1 Aumentar Cobertura para 95%+
**Status atual:** 94% (excelente)

**Implementação:**
```
Fase 1: Gap Analysis (Dia 1)
  - pytest --cov-report=html
  - Identificar linhas não cobertas
  - Priorizar código crítico (validadores, services)

Fase 2: Testes para Edge Cases (Dia 2-4)
  - Testar cenários de erro raro
  - Testar timezone edge cases
  - Testar concurrent operations extremes

Fase 3: Property-Based Testing (Dia 5-6)
  - Adicionar hypothesis ao requirements
  - Criar property tests para:
    * Validações (NIF, email, quantidades)
    * Cálculos financeiros
    * Invariants de stock
```

**Critérios de Aceite:**
- [ ] Cobertura ≥95%
- [ ] Zero linhas críticas sem teste
- [ ] Property tests para funções puras

---

### 3.2 Factory Boy
**Problema:** Fixtures manuais são verbosas e difíceis de manter

**Implementação:**
```
Fase 1: Setup (Dia 1)
  - Adicionar factory_boy ao requirements
  - Criar conftest.py com factories base

Fase 2: Factories por Modelo (Dia 2-4)
  - ProductFactory
  - CustomerFactory, SupplierFactory
  - InflowFactory, OutflowFactory
  - DeliveryFactory, PaymentFactory
  - AccountEntryFactory

Fase 3: Migração de Testes (Dia 5-7)
  - Refatorar testes existentes para usar factories
  - Manter cobertura durante migração
  - Documentar padrões de uso
```

**Arquivos afetados:**
- `tests/factories/` (novo)
- `conftest.py`
- Todos os arquivos de teste

---

### 3.3 Pre-commit Hooks
**Problema:** Código pode ser commitado sem formatação/linting

**Implementação:**
```
Fase 1: Configuração (Dia 1)
  - Adicionar pre-commit ao requirements-dev.txt
  - Criar .pre-commit-config.yaml
  - Configurar hooks:
    * black (formatação)
    * flake8 (linting)
    * isort (imports)
    * prettier (JS/CSS)

Fase 2: Integração CI (Dia 2)
  - Adicionar pre-commit check no GitHub Actions
  - Fail build se pre-commit falhar

Fase 3: Rollout (Dia 3)
  - Instalar pre-commit hooks localmente
  - Documentar para equipe
```

**Arquivos afetados:**
- `.pre-commit-config.yaml` (novo)
- `requirements-dev.txt`
- `.github/workflows/ci.yml` (se existir)

---

## 4. PERFORMANCE (Prioridade: MÉDIA)

### 4.1 Cache de Consultas Pesadas
**Status atual:** Dashboard com cache (implementado)

**Implementação:**
```
Fase 1: Identificação (Dia 1)
  - Django Debug Toolbar para identificar queries lentas
  - Profiling de reports grandes
  - Listar queries >100ms

Fase 2: Cache por Report (Dia 2-4)
  - StockReport: cache 5min
  - AccountBalance: cache 2min
  - MovementHistory: cache 10min, invalidate on write

Fase 3: Cache Hierárquico (Dia 5)
  - Implementar cache warming para dados frequentes
  - Cache de agregações (sums, counts)
```

---

### 4.2 Otimização N+1 Contínua
**Implementação:**
```
Fase 1: Django Debug Toolbar (Dia 1)
  - Configurar toolbar para desenvolvimento
  - Documentar como usar

Fase 2: CI Check (Dia 2)
  - pytest-django-assert-num-queries
  - Fail test se queries excederem threshold

Fase 3: Audit Regular (Dia 3)
  - Monthly performance review
  - Slow query log analysis
```

---

## 5. UX/UI (Prioridade: BAIXA-MÉDIA)

### 5.1 Feedback de Operações
**Problema:** Usuário não tem confirmação visual de ações

**Implementação:**
```
Fase 1: Toast Notifications (Dia 1-2)
  - Adicionar biblioteca (ex: toastr.js)
  - Criar middleware para mensagens Django → toast
  - Estilizar conforme design system

Fase 2: Loading States (Dia 3)
  - Spinner global para submits
  - Disable buttons durante processamento
  - Timeout para operações longas

Fase 3: Confirmações (Dia 4)
  - Confirm dialog para deletes
  - Preview antes de bulk operations
```

**Arquivos afetados:**
- `app/static/js/notifications.js` (novo)
- `app/templates/base.html`
- Forms templates

---

### 5.2 Autocomplete e Busca Inteligente
**Implementação:**
```
Fase 1: Select2 Integration (Dia 1-2)
  - Adicionar Select2 a forms de FK
  - Products, Customers, Suppliers
  - Busca por nome, NIF, código

Fase 2: Quick Search (Dia 3-4)
  - Global search bar no header
  - Indexar campos relevantes
  - Resultados categorizados
```

---

## 6. DEVOPS E DEPLOY (Prioridade: ALTA)

### 6.1 Dockerização
**Implementação:**
```
Fase 1: Dockerfile Base (Dia 1-2)
  - Criar Dockerfile para aplicação Django
  - Multi-stage build para otimizar tamanho
  - Configurar environment variables

Fase 2: Docker Compose (Dia 3-4)
  - Serviços: web, db, redis, celery-worker, celery-beat
  - Volumes para media files e backups
  - Networks isolados

Fase 3: Production Ready (Dia 5-6)
  - Nginx reverse proxy
  - SSL/TLS configuration
  - Health checks
  - Logging centralizado
```

**Arquivos afetados:**
- `Dockerfile` (novo)
- `docker-compose.yml` (novo)
- `docker-compose.prod.yml` (novo)
- `.dockerignore` (novo)

---

### 6.2 CI/CD Pipeline
**Implementação:**
```
Fase 1: GitHub Actions (Dia 1-2)
  - Workflow: lint, test, deploy
  - Matrix testing (Python versions)
  - Coverage reporting

Fase 2: Deploy Automático (Dia 3-4)
  - Deploy staging em PR merge
  - Deploy production em tag
  - Rollback automático se health check falhar

Fase 3: Quality Gates (Dia 5)
  - Block merge se coverage <90%
  - Block merge se tests falharem
  - Security scanning (bandit)
```

**Arquivos afetados:**
- `.github/workflows/ci.yml` (novo)
- `.github/workflows/deploy.yml` (novo)

---

### 6.3 Health Checks
**Implementação:**
```
Fase 1: Endpoint Básico (Dia 1)
  - GET /health/ (status 200 se OK)
  - Verificar database connection
  - Verificar Redis connection

Fase 2: Deep Health Check (Dia 2)
  - Verificar Celery worker alive
  - Verificar disk space
  - Verificar migrations applied

Fase 3: Monitoring Integration (Dia 3)
  - Prometheus metrics endpoint
  - Uptime monitoring integration
```

**Arquivos afetados:**
- `app/views.py` (health view)
- `app/urls.py`

---

## 7. DOCUMENTAÇÃO (Prioridade: MÉDIA)

### 7.1 API Documentation
**Implementação:**
```
Fase 1: Swagger (Dia 1-2)
  - drf-spectacular se DRF implementado
  - Ou Sphinx para API documentation
  - Exemplos de requests/responses

Fase 2: Runbook (Dia 3-4)
  - Procedimentos de troubleshooting
  - FAQ para erros comuns
  - Contact points para suporte
```

---

### 7.2 CHANGELOG Automatizado
**Implementação:**
```
Fase 1: Conventional Commits (Dia 1)
  - Documentar padrão de commits
  - feat:, fix:, chore:, etc.
  - Commitlint para validar

Fase 2: Auto-Generate (Dia 2)
  - github-changelog-generator
  - Integrar no release workflow
  - SemVer versioning
```

---

## CRONOGRAMA RESUMIDO

| Fase | Duração | Entregáveis |
|------|---------|-------------|
| **Segurança** | 2 semanas | CSP, Rate limiting, Upload validation |
| **Arquitetura** | 2 semanas | Service layer, Monitoramento Celery |
| **Testes** | 1 semana | 95% coverage, Factory Boy, Pre-commit |
| **Performance** | 1 semana | Cache queries, N+1 prevention |
| **UX/UI** | 1 semana | Notifications, Autocomplete |
| **DevOps** | 2 semanas | Docker, CI/CD, Health checks |
| **Documentação** | 1 semana | API docs, CHANGELOG |

**Total estimado:** 8-10 semanas (dependendo de prioridades e recursos)

---

## MATRIZ DE RISCOS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| CSP quebrar funcionalidades | Alta | Médio | Fase report-only, testes extensivos |
| Service layer introduzir bugs | Média | Alto | Manter backward compat, testes |
| Docker complexidade | Baixa | Baixo | Documentação clara, exemplos |
| Performance regression | Média | Médio | Load testing antes de deploy |
| Team resistance a mudanças | Média | Baixo | Training, documentação, phased rollout |

---

## CHECKLIST PRÉ-IMPLEMENTAÇÃO

- [ ] Backup completo da base de dados produção
- [ ] Ambiente staging idêntico a produção
- [ ] Suite de testes passando (423 tests)
- [ ] Code review para cada fase
- [ ] Rollback plan documentado
- [ ] Stakeholders alinhados com cronograma
- [ ] Monitoramento configurado (Sentry, logs)

---

## MÉTRICAS DE SUCESSO

1. **Segurança:** Zero vulnerabilidades críticas identificadas em pentest
2. **Qualidade:** ≥95% code coverage, zero linting errors
3. **Performance:** Page load <2s, 99th percentile API response <500ms
4. **Disponibilidade:** 99.9% uptime, health checks passing
5. **DevOps:** Deploy time <10min, rollback <5min
6. **UX:** User satisfaction score >4/5 em survey pós-implementação

---

## PRÓXIMOS PASSOS IMEDIATOS

1. **Semana 1:**
   - [ ] Aprovar este plano com stakeholders
   - [ ] Setup ambiente de desenvolvimento
   - [ ] Iniciar Fase 1 de Segurança (CSP)
   - [ ] Configurar pre-commit hooks

2. **Semana 2:**
   - [ ] Continuar Segurança (Rate limiting)
   - [ ] Iniciar Service Layer design
   - [ ] Factory Boy setup

3. **Revisões:**
   - Daily standup para blockers
   - Weekly demo de progresso
   - Bi-weekly retrospective

---

**Responsável:** [A definir]
**Revisão do Plano:** 2026-05-27
**Versão:** 1.0