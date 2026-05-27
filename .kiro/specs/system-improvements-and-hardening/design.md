# Documento de Design

## Introdução

Este documento descreve o design técnico para implementar 27 melhorias críticas e importantes no Sistema de Gestão de Stocks e Contas (SGE). O design está organizado por áreas funcionais e prioridades, fornecendo soluções detalhadas para cada requisito.

## Visão Geral da Arquitetura do Sistema

O SGE é uma aplicação Django com a seguinte estrutura:
- **13 modelos** distribuídos em 10 apps Django
- **60+ views** para operações CRUD e relatórios
- **93 testes** existentes que devem continuar a passar
- **Apps principais**: products, inflows, outflows, customers, suppliers, payments, accounts, audit, reports

### Arquitetura Atual

```
┌─────────────────────────────────────────────────────────┐
│                    Django Application                    │
├─────────────────────────────────────────────────────────┤
│  Products │ Inflows │ Outflows │ Customers │ Suppliers  │
│  Payments │ Accounts │ Audit │ Reports │ Users         │
├─────────────────────────────────────────────────────────┤
│                    SQLite Database                       │
└─────────────────────────────────────────────────────────┘
```

### Arquitetura Alvo

```
┌─────────────────────────────────────────────────────────┐
│                 Django Application Layer                 │
├─────────────────────────────────────────────────────────┤
│  Rate Limiter │ CSRF Protection │ Audit Middleware      │
├─────────────────────────────────────────────────────────┤
│  Business Logic Layer (Apps)                            │
│  + Concurrency Control                                  │
│  + Enhanced Validation                                  │
│  + Query Optimization                                   │
├─────────────────────────────────────────────────────────┤
│  Celery Task Queue  │  Redis Cache & Broker             │
├─────────────────────────────────────────────────────────┤
│  SQLite Database + Indexes + Constraints                │
├─────────────────────────────────────────────────────────┤
│  Sentry Monitoring │ Log Rotation │ Automated Backups   │
└─────────────────────────────────────────────────────────┘
```

## Decisões de Design

### Adições à Stack Tecnológica

1. **Redis**: Message broker para Celery e cache backend
2. **Celery**: Task queue para operações assíncronas
3. **Celery Beat**: Scheduler para tarefas periódicas
4. **Sentry SDK**: Monitoramento de erros
5. **django-ratelimit**: Rate limiting para autenticação


## P0 - Segurança Crítica e Integridade de Dados (Requisitos 1-6)

### Requisito 1: Controlo de Concorrência em Operações de Stock

**Padrão de Design**: Bloqueio Pessimista com Select For Update

**Implementação**:

```python
# outflows/views.py
class OutflowUpdateView(LoginRequiredMixin, UpdateView):
    def form_valid(self, form):
        with transaction.atomic():
            # Acquire lock on product before validation
            product = Product.objects.select_for_update().get(
                pk=form.cleaned_data['product'].pk
            )
            
            # Validate stock availability with locked product
            if product.quantity < form.cleaned_data['quantity']:
                form.add_error('quantity', 'Stock insuficiente')
                return self.form_invalid(form)
            
            # Update stock atomically
            product.quantity -= form.cleaned_data['quantity']
            product.save()
            
            return super().form_valid(form)
```

**Componentes Principais**:
- `transaction.atomic()`: Garante atomicidade
- `select_for_update()`: Adquire lock pessimista na linha
- Lock timeout: Django default (depende do backend)
- Rollback automático em caso de exceção

**Ficheiros a Modificar**:
- `outflows/views.py`: OutflowCreateView, OutflowUpdateView
- `outflows/models.py`: Delivery.save() method
- `products/views.py`: ProductUpdateView (se atualizar quantity diretamente)


### Requisito 2: Validação de Quantidades Negativas

**Padrão de Design**: Validação Multi-Camada (Formulário + Base de Dados)

**Implementação**:

```python
# products/forms.py
from django.core.validators import MinValueValidator

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise ValidationError('Quantidade não pode ser negativa')
        return quantity

# products/models.py
class Product(models.Model):
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Quantidade em stock'
    )
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='product_quantity_non_negative'
            )
        ]
```

**Componentes Principais**:
- Form-level validation: Primeira linha de defesa
- Model validators: Validação no save()
- Database constraints: Garantia final ao nível da BD

**Ficheiros a Modificar**:
- `products/forms.py`: ProductForm
- `inflows/forms.py`: InflowForm
- `outflows/forms.py`: OutflowForm, DeliveryForm
- `products/models.py`: Product model
- `inflows/models.py`: Inflow model
- `outflows/models.py`: Outflow, Delivery models
- Nova migration para adicionar CheckConstraints


### Requisito 3: Eliminação Atómica de Entregas

**Padrão de Design**: Eliminação Envolvida em Transação com Restauro de Stock

**Implementação**:

```python
# outflows/models.py
class Delivery(models.Model):
    # ... existing fields ...
    
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Lock product and outflow
            product = Product.objects.select_for_update().get(
                pk=self.outflow.product.pk
            )
            outflow = Outflow.objects.select_for_update().get(
                pk=self.outflow.pk
            )
            
            # Restore stock
            product.quantity += self.final_quantity
            product.save()
            
            # Update outflow delivered quantity
            outflow.quantity_delivered -= self.final_quantity
            outflow.save()
            
            # Delete delivery
            super().delete(*args, **kwargs)
```

**Componentes Principais**:
- Override `delete()` method
- Wrap em `transaction.atomic()`
- Lock related objects com `select_for_update()`
- Rollback automático se qualquer operação falhar

**Ficheiros a Modificar**:
- `outflows/models.py`: Delivery.delete() method
- `outflows/views.py`: DeliveryDeleteView (garantir que usa model delete)


### Requisito 4: Invalidação de Cache do Dashboard

**Padrão de Design**: Invalidação de Cache Baseada em Sinais

**Implementação**:

```python
# app/cache_utils.py
from django.core.cache import cache

DASHBOARD_CACHE_KEY = 'dashboard_data'

def invalidate_dashboard_cache():
    """Invalidate dashboard cache"""
    cache.delete(DASHBOARD_CACHE_KEY)

# products/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from app.cache_utils import invalidate_dashboard_cache

@receiver([post_save, post_delete], sender=Product)
def invalidate_cache_on_product_change(sender, **kwargs):
    invalidate_dashboard_cache()

# Similar signals for: Inflow, Outflow, Delivery, Payment, 
# CustomerAccountEntry, SupplierAccountEntry
```

**Dashboard View with Caching**:

```python
# app/views.py
from django.core.cache import cache
from app.cache_utils import DASHBOARD_CACHE_KEY

def dashboard_view(request):
    data = cache.get(DASHBOARD_CACHE_KEY)
    
    if data is None:
        data = {
            'total_products': Product.objects.count(),
            'low_stock_products': Product.objects.filter(quantity__lt=10).count(),
            'pending_outflows': Outflow.objects.filter(status='pending').count(),
            # ... other dashboard metrics
        }
        cache.set(DASHBOARD_CACHE_KEY, data, timeout=3600)  # 1 hour
    
    return render(request, 'dashboard.html', {'data': data})
```

**Key Components**:
- Centralized cache key management
- Signal handlers para invalidação automática
- Cache timeout como fallback

**Files to Create/Modify**:
- `app/cache_utils.py`: NEW - Utility functions
- `products/signals.py`: NEW - Signal handlers
- `inflows/signals.py`: Adicionar cache invalidation
- `outflows/signals.py`: Adicionar cache invalidation
- `payments/signals.py`: Adicionar cache invalidation
- `accounts/signals.py`: Adicionar cache invalidation
- `app/views.py`: Adicionar caching ao dashboard


### Requirement 5: Authentication Rate Limiting

**Design Pattern**: Decorator-Based Rate Limiting with django-ratelimit

**Implementation**:

```python
# users/views.py
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.views import LoginView
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    
    @ratelimit(key='user_or_ip', rate='5/15m', method='POST', block=True)
    def post(self, request, *args, **kwargs):
        # Check if rate limited
        if getattr(request, 'limited', False):
            logger.warning(
                f'Rate limit exceeded for login attempt. '
                f'Username: {request.POST.get("username")}, '
                f'IP: {request.META.get("REMOTE_ADDR")}'
            )
            messages.error(
                request,
                'Muitas tentativas de login falhadas. '
                'Por favor aguarde 30 minutos antes de tentar novamente.'
            )
            return self.render_to_response(self.get_context_data())
        
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Reset rate limit on successful login
        cache_key = f'rl:user:{form.cleaned_data["username"]}'
        cache.delete(cache_key)
        return super().form_valid(form)
```

**Settings Configuration**:

```python
# app/settings.py
RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_VIEW = 'users.views.rate_limit_exceeded'
```

**Key Components**:
- `django-ratelimit` library
- Rate: 5 tentativas em 15 minutos
- Block duration: 30 minutos (2x window)
- Key: combinação de username e IP
- Logging de violações

**Files to Modify**:
- `requirements.txt`: Adicionar django-ratelimit
- `users/views.py`: CustomLoginView com rate limiting
- `users/urls.py`: Usar CustomLoginView
- `app/settings.py`: Configuração do ratelimit


### Requirement 6: CSRF Protection for AJAX Requests

**Design Pattern**: JavaScript CSRF Token Injection

**Implementation**:

```javascript
// app/static/js/csrf.js
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Setup AJAX to include CSRF token
function setupCSRF() {
    // For jQuery
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    
    // For Fetch API
    window.fetchWithCSRF = function(url, options = {}) {
        options.headers = options.headers || {};
        if (!options.method || !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(options.method.toUpperCase())) {
            options.headers['X-CSRFToken'] = csrftoken;
        }
        return fetch(url, options);
    };
}

// Auto-setup on page load
document.addEventListener('DOMContentLoaded', setupCSRF);
```

**Template Integration**:

```html
<!-- app/templates/base.html -->
{% load static %}
<script src="{% static 'js/csrf.js' %}"></script>
```

**Key Components**:
- Utility function para extrair CSRF token do cookie
- Auto-setup para jQuery AJAX
- Wrapper para Fetch API
- Exclusão de métodos safe (GET, HEAD, OPTIONS, TRACE)

**Files to Create/Modify**:
- `app/static/js/csrf.js`: NEW - CSRF utility
- `app/templates/base.html`: Include CSRF script
- Todas as views AJAX existentes: Verificar CSRF enforcement


## P1 - Important Performance and Validation (Requirements 7-18)

### Requirement 7: Query Optimization for Account Balance Views

**Design Pattern**: Eager Loading with select_related and prefetch_related

**Implementation**:

```python
# accounts/views.py
class CustomerBalanceListView(LoginRequiredMixin, ListView):
    model = CustomerAccountEntry
    template_name = 'accounts/customer_balance_list.html'
    paginate_by = 50
    
    def get_queryset(self):
        return CustomerAccountEntry.objects.select_related(
            'customer',
            'outflow',
            'outflow__product',
            'payment'
        ).order_by('-created_at')

class SupplierBalanceListView(LoginRequiredMixin, ListView):
    model = SupplierAccountEntry
    template_name = 'accounts/supplier_balance_list.html'
    paginate_by = 50
    
    def get_queryset(self):
        return SupplierAccountEntry.objects.select_related(
            'supplier',
            'inflow',
            'inflow__product',
            'payment'
        ).order_by('-created_at')
```

**Query Analysis**:
- **Before**: 1 query inicial + N queries para cada entry = N+1 queries
- **After**: 1 query com JOINs = 1 query total
- **Performance Gain**: ~95% reduction em queries para 50 entries

**Files to Modify**:
- `accounts/views.py`: CustomerBalanceListView, SupplierBalanceListView
- `accounts/models.py`: Adicionar select_related em managers customizados (opcional)


### Requirement 8: Composite Database Indexes

**Design Pattern**: Multi-Column Indexes for Common Query Patterns

**Implementation**:

```python
# accounts/models.py
class CustomerAccountEntry(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # ... other fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at'], 
                        name='customer_entry_idx'),
            models.Index(fields=['created_at'], 
                        name='customer_entry_date_idx'),
        ]

class SupplierAccountEntry(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # ... other fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['supplier', '-created_at'], 
                        name='supplier_entry_idx'),
            models.Index(fields=['created_at'], 
                        name='supplier_entry_date_idx'),
        ]

# outflows/models.py
class Outflow(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # ... other fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at'], 
                        name='outflow_customer_idx'),
            models.Index(fields=['status', '-created_at'], 
                        name='outflow_status_idx'),
        ]

# inflows/models.py
class Inflow(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # ... other fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['supplier', '-created_at'], 
                        name='inflow_supplier_idx'),
        ]
```

**Index Strategy**:
- Composite indexes para queries com filtro + ordenação
- Ordem: campo de filtro primeiro, campo de ordenação depois
- Descending order (-created_at) para queries ORDER BY created_at DESC

**Files to Modify**:
- `accounts/models.py`: Adicionar indexes
- `outflows/models.py`: Adicionar indexes
- `inflows/models.py`: Adicionar indexes
- Nova migration para criar indexes


### Requirement 9: Email Validation Enhancement

**Design Pattern**: Django Built-in EmailValidator

**Implementation**:

```python
# customers/models.py
from django.core.validators import EmailValidator

class Customer(models.Model):
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        validators=[EmailValidator(message='Introduza um endereço de email válido')],
        help_text='Email do cliente'
    )

# suppliers/models.py
class Supplier(models.Model):
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        validators=[EmailValidator(message='Introduza um endereço de email válido')],
        help_text='Email do fornecedor'
    )
```

**Key Components**:
- `EmailField`: Já inclui validação básica
- `EmailValidator`: Validação adicional customizada
- Mensagem de erro em português
- Permite null/blank (email opcional)

**Files to Modify**:
- `customers/models.py`: Customer.email field
- `suppliers/models.py`: Supplier.email field
- `customers/forms.py`: Verificar validação no form
- `suppliers/forms.py`: Verificar validação no form


### Requirement 10: Angolan NIF Validation

**Design Pattern**: Custom Validator for Angolan Tax ID

**Implementation**:

```python
# app/validators.py
from django.core.exceptions import ValidationError
import re

def validate_angolan_nif(value):
    """
    Validate Angolan NIF (Número de Identificação Fiscal)
    Format: 9 numeric digits
    """
    if value is None or value == '':
        return  # Allow blank/null
    
    # Remove whitespace
    value = str(value).strip()
    
    # Check format: exactly 9 digits
    if not re.match(r'^\d{9}$', value):
        raise ValidationError(
            'NIF deve conter exatamente 9 dígitos numéricos',
            code='invalid_nif'
        )

# customers/models.py
from app.validators import validate_angolan_nif

class Customer(models.Model):
    nif = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        validators=[validate_angolan_nif],
        help_text='Número de Identificação Fiscal (9 dígitos)',
        verbose_name='NIF'
    )

# suppliers/models.py
class Supplier(models.Model):
    nif = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        validators=[validate_angolan_nif],
        help_text='Número de Identificação Fiscal (9 dígitos)',
        verbose_name='NIF'
    )
```

**Validation Rules**:
- Exactly 9 numeric digits
- No letters or special characters
- Optional (can be null/blank)
- Whitespace trimmed before validation

**Files to Create/Modify**:
- `app/validators.py`: NEW - Custom validators
- `customers/models.py`: Customer.nif field
- `suppliers/models.py`: Supplier.nif field
- `customers/forms.py`: Form validation
- `suppliers/forms.py`: Form validation


### Requirement 11: Log Rotation Configuration

**Design Pattern**: RotatingFileHandler with Size-Based Rotation

**Implementation**:

```python
# app/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django_errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

**Rotation Behavior**:
- Max file size: 10 MB
- Backup count: 5 files
- Naming: django.log, django.log.1, django.log.2, ..., django.log.5
- Oldest backup deleted when creating new backup

**Files to Modify**:
- `app/settings.py`: LOGGING configuration


### Requirement 12: Error Monitoring Integration

**Design Pattern**: Sentry SDK Integration

**Implementation**:

```python
# app/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
import os

# Sentry Configuration
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        send_default_pii=False,  # Don't send personally identifiable information
        environment='production' if not DEBUG else 'development',
        release=os.environ.get('APP_VERSION', 'unknown'),
    )
```

**Environment Variables**:

```bash
# .env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
APP_VERSION=1.0.0
```

**Custom Error Capture**:

```python
# Example usage in views
from sentry_sdk import capture_exception, capture_message

try:
    # risky operation
    process_payment(payment_id)
except PaymentError as e:
    capture_exception(e)
    logger.error(f'Payment processing failed: {e}')
```

**Key Components**:
- Automatic exception capture
- Request context included
- User information (if authenticated)
- Environment tagging (dev/prod)
- Performance monitoring (10% sample)
- Graceful degradation se DSN não configurado

**Files to Modify**:
- `requirements.txt`: Adicionar sentry-sdk
- `app/settings.py`: Sentry initialization
- `.env.example`: Adicionar SENTRY_DSN


### Requirement 13: Automated Database Backup

**Design Pattern**: Celery Periodic Task with Backup Rotation

**Implementation**:

```python
# app/tasks.py
from celery import shared_task
from django.conf import settings
from pathlib import Path
import shutil
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def backup_database():
    """
    Create a timestamped backup of the SQLite database
    and maintain only the last 30 backups
    """
    try:
        # Get database path
        db_path = Path(settings.DATABASES['default']['NAME'])
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f'db_backup_{timestamp}.sqlite3'
        
        # Copy database
        shutil.copy2(db_path, backup_path)
        
        # Verify backup
        if not backup_path.exists() or backup_path.stat().st_size == 0:
            raise Exception('Backup file is empty or does not exist')
        
        logger.info(f'Database backup created: {backup_path}')
        
        # Clean old backups (keep last 30)
        backups = sorted(backup_dir.glob('db_backup_*.sqlite3'))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()
                logger.info(f'Deleted old backup: {old_backup}')
        
        return f'Backup successful: {backup_path}'
        
    except Exception as e:
        logger.error(f'Database backup failed: {e}')
        raise

# app/celery.py
from celery import Celery
from celery.schedules import crontab

app = Celery('sge')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'backup-database-daily': {
        'task': 'app.tasks.backup_database',
        'schedule': crontab(hour=2, minute=0),  # 02:00 AM daily
    },
}
```

**Settings Configuration**:

```python
# app/settings.py
BACKUP_DIR = os.environ.get('BACKUP_DIR', BASE_DIR / 'backups')
```

**Files to Create/Modify**:
- `app/tasks.py`: NEW - Celery tasks
- `app/celery.py`: NEW - Celery configuration
- `app/__init__.py`: Import celery app
- `app/settings.py`: BACKUP_DIR setting
- `.env.example`: BACKUP_DIR variable


### Requirement 14: Future Date Validation for Payments

**Design Pattern**: Custom Clean Method with Timezone-Aware Validation

**Implementation**:

```python
# payments/forms.py
from django.utils import timezone
from datetime import timedelta
import pytz

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date:
            # Get current date in Africa/Luanda timezone
            luanda_tz = pytz.timezone('Africa/Luanda')
            now = timezone.now().astimezone(luanda_tz)
            today = now.date()
            
            # Allow up to 1 day in future (for timezone tolerance)
            max_date = today + timedelta(days=1)
            
            if date > max_date:
                raise ValidationError(
                    'Data de pagamento não pode ser no futuro',
                    code='future_date'
                )
        
        return date

# payments/models.py
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import pytz

def validate_payment_date(value):
    """Validate payment date is not in the future"""
    if value:
        luanda_tz = pytz.timezone('Africa/Luanda')
        now = timezone.now().astimezone(luanda_tz)
        today = now.date()
        max_date = today + timedelta(days=1)
        
        if value > max_date:
            raise ValidationError(
                'Data de pagamento não pode ser no futuro',
                code='future_date'
            )

class Payment(models.Model):
    date = models.DateField(
        validators=[validate_payment_date],
        help_text='Data do pagamento'
    )
```

**Key Components**:
- Timezone-aware validation (Africa/Luanda)
- 1-day tolerance para edge cases
- Validação em form e model
- Permite datas passadas sem restrição

**Files to Modify**:
- `payments/forms.py`: PaymentForm.clean_date()
- `payments/models.py`: Payment.date validator
- `requirements.txt`: Verificar pytz instalado


### Requirement 15: Thread-Local Cleanup in Audit Middleware

**Design Pattern**: Try-Finally Pattern for Resource Cleanup

**Implementation**:

```python
# audit/middleware.py
import threading

_thread_locals = threading.local()

def get_current_user():
    """Get the current user from thread-local storage"""
    return getattr(_thread_locals, 'user', None)

def set_current_user(user):
    """Set the current user in thread-local storage"""
    _thread_locals.user = user

def clear_current_user():
    """Clear the current user from thread-local storage"""
    if hasattr(_thread_locals, 'user'):
        delattr(_thread_locals, 'user')

class AuditMiddleware:
    """Middleware to track current user for audit logging"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set current user at start of request
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Always clear thread-local storage
            clear_current_user()
```

**Key Components**:
- `threading.local()`: Thread-safe storage
- `try-finally`: Garantia de cleanup
- Cleanup mesmo em caso de exceção
- Isolation entre requests

**Files to Modify**:
- `audit/middleware.py`: AuditMiddleware com try-finally
- `audit/signals.py`: Usar get_current_user() helper


### Requirement 16: Paginated Export Operations

**Design Pattern**: Iterator-Based Streaming with Celery for Large Exports

**Implementation**:

```python
# reports/views.py
from django.http import StreamingHttpResponse
from django.db import connection
import csv

class ExportMixin:
    """Mixin for memory-efficient exports"""
    
    def export_csv_streaming(self, queryset, filename):
        """Stream CSV export using iterator"""
        
        def csv_generator():
            # Get field names
            model = queryset.model
            field_names = [f.name for f in model._meta.fields]
            
            # Write header
            yield ','.join(field_names) + '\n'
            
            # Stream rows in chunks
            for obj in queryset.iterator(chunk_size=500):
                row = [str(getattr(obj, field)) for field in field_names]
                yield ','.join(row) + '\n'
        
        response = StreamingHttpResponse(
            csv_generator(),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

# reports/tasks.py
from celery import shared_task
from openpyxl import Workbook
import logging

logger = logging.getLogger(__name__)

@shared_task(time_limit=300)  # 5 minute timeout
def generate_large_excel_export(model_name, filters, user_email):
    """
    Generate large Excel export in background
    """
    try:
        # Get model and queryset
        model = apps.get_model('app_label', model_name)
        queryset = model.objects.filter(**filters)
        
        # Create workbook
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        
        # Write header
        field_names = [f.name for f in model._meta.fields]
        ws.append(field_names)
        
        # Write data in chunks
        for obj in queryset.iterator(chunk_size=500):
            row = [getattr(obj, field) for field in field_names]
            ws.append(row)
        
        # Save to file
        filename = f'/tmp/export_{model_name}_{timezone.now().timestamp()}.xlsx'
        wb.save(filename)
        
        # Send email with download link
        send_export_email(user_email, filename)
        
        return f'Export completed: {filename}'
        
    except Exception as e:
        logger.error(f'Export failed: {e}')
        raise
```

**Export Decision Logic**:

```python
# reports/views.py
class ReportExportView(View):
    def get(self, request):
        queryset = self.get_queryset()
        count = queryset.count()
        
        if count > 1000:
            # Delegate to Celery
            task = generate_large_excel_export.delay(
                model_name=self.model.__name__,
                filters=self.get_filters(),
                user_email=request.user.email
            )
            messages.info(
                request,
                f'Export iniciado. Receberá email quando concluído. Task ID: {task.id}'
            )
            return redirect('reports:export_status', task_id=task.id)
        else:
            # Stream directly
            return self.export_csv_streaming(queryset, 'export.csv')
```

**Key Components**:
- `iterator(chunk_size=500)`: Chunked database queries
- `StreamingHttpResponse`: Streaming para cliente
- Celery task para exports > 1000 records
- Email notification quando completo

**Files to Modify**:
- `reports/views.py`: Adicionar ExportMixin
- `reports/tasks.py`: NEW - Export tasks
- Todas as views de export: Usar ExportMixin


### Requirement 17: Permission Validation for Bulk Operations

**Design Pattern**: Permission Check Before Bulk Delete

**Implementation**:

```python
# app/mixins.py
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)

class BulkDeleteMixin(PermissionRequiredMixin):
    """Mixin for bulk delete operations with permission validation"""
    
    def get_permission_required(self):
        """Get delete permission for the model"""
        opts = self.model._meta
        return [f'{opts.app_label}.delete_{opts.model_name}']
    
    def bulk_delete(self, request, queryset):
        """
        Perform bulk delete with permission validation and logging
        """
        # Check permission
        if not request.user.has_perm(self.get_permission_required()[0]):
            logger.warning(
                f'Unauthorized bulk delete attempt by {request.user.username} '
                f'on {self.model.__name__}'
            )
            raise PermissionDenied('Não tem permissão para eliminar estes registos')
        
        # Log bulk delete
        count = queryset.count()
        logger.info(
            f'Bulk delete: {count} {self.model.__name__} records '
            f'by {request.user.username} at {timezone.now()}'
        )
        
        # Perform delete
        deleted_count, _ = queryset.delete()
        
        return deleted_count

# Example usage in admin
# products/admin.py
from app.mixins import BulkDeleteMixin

@admin.register(Product)
class ProductAdmin(BulkDeleteMixin, admin.ModelAdmin):
    actions = ['bulk_delete_selected']
    
    def bulk_delete_selected(self, request, queryset):
        """Bulk delete action with permission check"""
        try:
            count = self.bulk_delete(request, queryset)
            self.message_user(
                request,
                f'{count} produtos eliminados com sucesso'
            )
        except PermissionDenied as e:
            self.message_user(request, str(e), level='error')
```

**Key Components**:
- Permission check antes de delete
- Single permission check (não N checks)
- Logging de todas as operações bulk
- PermissionDenied exception se não autorizado

**Files to Modify**:
- `app/mixins.py`: Adicionar BulkDeleteMixin
- Todos os admin.py: Usar BulkDeleteMixin para bulk actions
- Todas as views com bulk delete: Adicionar permission check


### Requirement 18: Exception Handling in Audit Signals

**Design Pattern**: Defensive Signal Handlers with Try-Except

**Implementation**:

```python
# audit/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from audit.models import AuditLog
from audit.middleware import get_current_user
import logging

logger = logging.getLogger(__name__)

def create_audit_log(instance, action):
    """
    Create audit log entry with exception handling
    Returns True if successful, False otherwise
    """
    try:
        user = get_current_user()
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=instance.pk,
            object_repr=str(instance)
        )
        return True
    except Exception as e:
        logger.error(
            f'Failed to create audit log for {instance.__class__.__name__} '
            f'{instance.pk}: {e}',
            exc_info=True
        )
        return False

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Audit log for model saves"""
    # Skip audit models to avoid recursion
    if sender.__name__ == 'AuditLog':
        return
    
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(instance, action)

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Audit log for model deletes"""
    # Skip audit models
    if sender.__name__ == 'AuditLog':
        return
    
    create_audit_log(instance, 'DELETE')
```

**Key Components**:
- Try-except em todas as operações de audit
- Logging de erros sem propagar exceção
- Business transaction não afetada por falhas de audit
- Recursion prevention (skip AuditLog model)

**Files to Modify**:
- `audit/signals.py`: Adicionar exception handling
- `audit/models.py`: Verificar que save() não lança exceções


## P2-P3 - Quality and Feature Improvements (Requirements 19-27)

### Requirement 19: Test Coverage Improvement

**Design Pattern**: Comprehensive Test Suite with Coverage Reporting

**Implementation**:

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = app.settings
python_files = tests.py test_*.py *_tests.py
addopts = 
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

# Example test structure
# products/tests/test_models.py
from django.test import TestCase
from products.models import Product

class ProductModelTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            quantity=100,
            price=50.00
        )
    
    def test_product_creation(self):
        """Test product is created correctly"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.quantity, 100)
    
    def test_quantity_non_negative_constraint(self):
        """Test quantity cannot be negative"""
        with self.assertRaises(ValidationError):
            self.product.quantity = -10
            self.product.full_clean()
    
    def test_str_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.product), 'Test Product')

# products/tests/test_views.py
class ProductViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.client.login(username='test', password='pass')
    
    def test_product_list_view(self):
        """Test product list view"""
        response = self.client.get(reverse('products:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_list.html')
```

**Test Categories**:
1. **Model Tests**: Validation, methods, properties
2. **Form Tests**: Validation logic, clean methods
3. **View Tests**: HTTP responses, permissions, context
4. **Signal Tests**: Signal handlers execute correctly
5. **Middleware Tests**: Request/response processing
6. **Template Tag Tests**: Custom tags and filters
7. **Integration Tests**: End-to-end workflows

**Coverage Goals**:
- Overall: 80%+
- Models: 90%+
- Forms: 85%+
- Views: 75%+
- Utils: 90%+

**Files to Create**:
- `pytest.ini`: NEW - Pytest configuration
- `products/tests/`: Reorganizar em package
- `inflows/tests/`: Reorganizar em package
- `outflows/tests/`: Reorganizar em package
- Similar para todos os apps


### Requirement 20: Integration Test Suite

**Design Pattern**: TransactionTestCase for End-to-End Workflows

**Implementation**:

```python
# tests/integration/test_outflow_workflow.py
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from products.models import Product
from customers.models import Customer
from outflows.models import Outflow, Delivery

User = get_user_model()

class OutflowWorkflowIntegrationTest(TransactionTestCase):
    """Test complete outflow creation and delivery workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.customer = Customer.objects.create(name='Test Customer')
        self.product = Product.objects.create(
            name='Test Product',
            quantity=100,
            price=50.00
        )
    
    def test_complete_outflow_delivery_workflow(self):
        """Test creating outflow, adding deliveries, and stock updates"""
        # Step 1: Create outflow
        outflow = Outflow.objects.create(
            customer=self.customer,
            product=self.product,
            quantity=50,
            status='pending'
        )
        self.assertEqual(outflow.quantity_delivered, 0)
        
        # Step 2: Create first delivery
        delivery1 = Delivery.objects.create(
            outflow=outflow,
            quantity=20,
            final_quantity=20
        )
        
        # Verify stock decreased
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 80)
        
        # Verify outflow updated
        outflow.refresh_from_db()
        self.assertEqual(outflow.quantity_delivered, 20)
        self.assertEqual(outflow.status, 'partial')
        
        # Step 3: Create second delivery
        delivery2 = Delivery.objects.create(
            outflow=outflow,
            quantity=30,
            final_quantity=30
        )
        
        # Verify stock decreased again
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 50)
        
        # Verify outflow completed
        outflow.refresh_from_db()
        self.assertEqual(outflow.quantity_delivered, 50)
        self.assertEqual(outflow.status, 'delivered')
        
        # Step 4: Delete first delivery
        delivery1.delete()
        
        # Verify stock restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 70)
        
        # Verify outflow updated
        outflow.refresh_from_db()
        self.assertEqual(outflow.quantity_delivered, 30)
        self.assertEqual(outflow.status, 'partial')

# tests/integration/test_payment_workflow.py
class PaymentWorkflowIntegrationTest(TransactionTestCase):
    """Test payment and account reconciliation workflow"""
    
    def test_payment_creates_account_entry(self):
        """Test that payment creation updates account entries"""
        # Create outflow
        outflow = Outflow.objects.create(...)
        
        # Create payment
        payment = Payment.objects.create(
            outflow=outflow,
            amount=100.00
        )
        
        # Verify account entry created
        entry = CustomerAccountEntry.objects.get(payment=payment)
        self.assertEqual(entry.amount, 100.00)
        self.assertEqual(entry.customer, outflow.customer)
```

**Integration Test Scenarios**:
1. Outflow creation → Delivery → Stock update
2. Payment → Account entry creation
3. Inflow → Stock increase
4. User authentication → Authorization
5. Report generation with filters

**Performance Target**: < 5 minutes for full suite

**Files to Create**:
- `tests/integration/`: NEW - Integration test package
- `tests/integration/test_outflow_workflow.py`: NEW
- `tests/integration/test_payment_workflow.py`: NEW
- `tests/integration/test_inflow_workflow.py`: NEW
- `tests/integration/test_auth_workflow.py`: NEW
- `tests/integration/test_reports.py`: NEW


### Requirement 21: Code Duplication Refactoring

**Design Pattern**: Base Classes and Mixins for Shared Logic

**Implementation**:

```python
# reports/base.py
from django.views.generic import ListView
from django.http import HttpResponse
from datetime import datetime

class BaseReportView(ListView):
    """Base view for all reports with common functionality"""
    
    paginate_by = 50
    export_formats = ['csv', 'excel', 'pdf']
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = super().get_queryset()
        return self.apply_filters(queryset)
    
    def apply_filters(self, queryset):
        """Apply filters from request parameters"""
        # Date range filter
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add common context"""
        context = super().get_context_data(**kwargs)
        context['filters'] = self.get_active_filters()
        context['export_formats'] = self.export_formats
        return context
    
    def get_active_filters(self):
        """Get active filters for display"""
        filters = {}
        for key in ['start_date', 'end_date', 'customer', 'supplier']:
            value = self.request.GET.get(key)
            if value:
                filters[key] = value
        return filters
    
    def render_to_response(self, context, **response_kwargs):
        """Handle export formats"""
        export_format = self.request.GET.get('format')
        
        if export_format == 'csv':
            return self.export_csv()
        elif export_format == 'excel':
            return self.export_excel()
        elif export_format == 'pdf':
            return self.export_pdf()
        
        return super().render_to_response(context, **response_kwargs)
    
    def export_csv(self):
        """Export to CSV - to be implemented by subclasses"""
        raise NotImplementedError
    
    def export_excel(self):
        """Export to Excel - to be implemented by subclasses"""
        raise NotImplementedError
    
    def export_pdf(self):
        """Export to PDF - to be implemented by subclasses"""
        raise NotImplementedError

# reports/views.py - Refactored
class CustomerAccountReportView(BaseReportView):
    """Customer account report using base class"""
    
    model = CustomerAccountEntry
    template_name = 'reports/customer_account_report.html'
    
    def apply_filters(self, queryset):
        """Apply customer-specific filters"""
        queryset = super().apply_filters(queryset)
        
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset.select_related('customer', 'outflow', 'payment')
    
    def export_csv(self):
        """CSV export implementation"""
        # Specific implementation
        pass

class SupplierAccountReportView(BaseReportView):
    """Supplier account report using base class"""
    
    model = SupplierAccountEntry
    template_name = 'reports/supplier_account_report.html'
    
    def apply_filters(self, queryset):
        """Apply supplier-specific filters"""
        queryset = super().apply_filters(queryset)
        
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        return queryset.select_related('supplier', 'inflow', 'payment')
```

**Refactoring Benefits**:
- Shared filtering logic
- Shared pagination
- Shared export framework
- Consistent UI/UX
- 40%+ code reduction

**Files to Create/Modify**:
- `reports/base.py`: NEW - Base classes
- `reports/views.py`: Refactor to use base classes
- `reports/mixins.py`: NEW - Reusable mixins


### Requirement 22: File Upload Magic Bytes Validation

**Design Pattern**: Content-Type Validation with Magic Bytes

**Implementation**:

```python
# app/validators.py
from django.core.exceptions import ValidationError

# Magic bytes signatures
MAGIC_BYTES = {
    'pdf': b'%PDF',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
    'png': b'\x89PNG\r\n\x1a\n',
}

def validate_file_content(file):
    """
    Validate file content matches extension using magic bytes
    """
    if not file:
        return
    
    # Get file extension
    filename = file.name.lower()
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
    
    if ext not in MAGIC_BYTES:
        raise ValidationError(
            f'Tipo de arquivo não suportado: {ext}',
            code='unsupported_type'
        )
    
    # Read first bytes
    file.seek(0)
    header = file.read(8)
    file.seek(0)  # Reset for later use
    
    # Check magic bytes
    expected_magic = MAGIC_BYTES[ext]
    if not header.startswith(expected_magic):
        raise ValidationError(
            'Tipo de arquivo inválido. O conteúdo não corresponde à extensão.',
            code='invalid_content'
        )

# outflows/forms.py
from app.validators import validate_file_content

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = '__all__'
    
    def clean_shipping_guide(self):
        """Validate shipping guide file"""
        file = self.cleaned_data.get('shipping_guide')
        if file:
            validate_file_content(file)
        return file

# outflows/models.py
class Delivery(models.Model):
    shipping_guide = models.FileField(
        upload_to='shipping_guides/',
        validators=[validate_file_content],
        blank=True,
        null=True,
        help_text='Guia de remessa (PDF, JPG, PNG)'
    )
```

**Supported Formats**:
- PDF: %PDF
- JPEG: FF D8 FF
- PNG: 89 50 4E 47 0D 0A 1A 0A

**Security Benefits**:
- Prevents file type spoofing
- Blocks malicious files with fake extensions
- Validates before saving to disk

**Files to Modify**:
- `app/validators.py`: Adicionar validate_file_content
- `outflows/forms.py`: DeliveryForm validation
- `outflows/models.py`: Delivery.shipping_guide validator


### Requirement 23: Soft Delete for Delivery Model

**Design Pattern**: Soft Delete with Manager and QuerySet

**Implementation**:

```python
# app/models.py
from django.db import models
from django.utils import timezone

class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted objects"""
    
    def delete(self):
        """Soft delete all objects in queryset"""
        return self.update(is_deleted=True, deleted_at=timezone.now())
    
    def hard_delete(self):
        """Permanently delete objects"""
        return super().delete()
    
    def alive(self):
        """Return only non-deleted objects"""
        return self.filter(is_deleted=False)
    
    def deleted(self):
        """Return only deleted objects"""
        return self.filter(is_deleted=True)

class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()
    
    def all_with_deleted(self):
        """Return all objects including deleted"""
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """Return only deleted objects"""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()

class SoftDeleteModel(models.Model):
    """Abstract base model for soft delete functionality"""
    
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all including deleted
    
    class Meta:
        abstract = True
    
    def delete(self, *args, **kwargs):
        """Soft delete the object"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self):
        """Permanently delete the object"""
        super().delete()
    
    def restore(self):
        """Restore a soft-deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

# outflows/models.py
from app.models import SoftDeleteModel

class Delivery(SoftDeleteModel):
    outflow = models.ForeignKey(Outflow, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    final_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    # ... other fields ...
    
    def delete(self, *args, **kwargs):
        """Soft delete with stock adjustment"""
        with transaction.atomic():
            # Lock related objects
            product = Product.objects.select_for_update().get(
                pk=self.outflow.product.pk
            )
            outflow = Outflow.objects.select_for_update().get(
                pk=self.outflow.pk
            )
            
            # Restore stock
            product.quantity += self.final_quantity
            product.save()
            
            # Update outflow
            outflow.quantity_delivered -= self.final_quantity
            outflow.save()
            
            # Soft delete
            super().delete(*args, **kwargs)
    
    def restore(self):
        """Restore delivery and reverse stock adjustment"""
        with transaction.atomic():
            # Lock related objects
            product = Product.objects.select_for_update().get(
                pk=self.outflow.product.pk
            )
            outflow = Outflow.objects.select_for_update().get(
                pk=self.outflow.pk
            )
            
            # Decrease stock again
            product.quantity -= self.final_quantity
            product.save()
            
            # Update outflow
            outflow.quantity_delivered += self.final_quantity
            outflow.save()
            
            # Restore
            super().restore()

# outflows/views.py
class DeliveryTrashListView(LoginRequiredMixin, ListView):
    """View for soft-deleted deliveries"""
    
    model = Delivery
    template_name = 'outflows/delivery_trash.html'
    
    def get_queryset(self):
        return Delivery.all_objects.deleted_only()

class DeliveryRestoreView(LoginRequiredMixin, View):
    """Restore a soft-deleted delivery"""
    
    def post(self, request, pk):
        delivery = get_object_or_404(Delivery.all_objects, pk=pk, is_deleted=True)
        delivery.restore()
        messages.success(request, 'Entrega restaurada com sucesso')
        return redirect('outflows:delivery_list')
```

**Key Features**:
- Default manager excludes deleted objects
- `all_objects` manager includes deleted
- Atomic stock adjustments on delete/restore
- Trash view for recovery
- Admin-only hard delete

**Files to Create/Modify**:
- `app/models.py`: NEW - SoftDeleteModel base class
- `outflows/models.py`: Delivery inherits SoftDeleteModel
- `outflows/views.py`: Trash and restore views
- `outflows/urls.py`: Trash and restore URLs
- `outflows/templates/`: Trash list template
- Nova migration para adicionar is_deleted, deleted_at


### Requirement 24: Database Uniqueness Constraints

**Design Pattern**: Unique Constraints with Conditional Indexes

**Implementation**:

```python
# customers/models.py
class Customer(models.Model):
    name = models.CharField(max_length=200)
    nif = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        validators=[validate_angolan_nif],
        verbose_name='NIF'
    )
    # ... other fields ...
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nif'],
                condition=models.Q(nif__isnull=False),
                name='unique_customer_nif'
            )
        ]

# suppliers/models.py
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    nif = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        validators=[validate_angolan_nif],
        verbose_name='NIF'
    )
    # ... other fields ...
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nif'],
                condition=models.Q(nif__isnull=False),
                name='unique_supplier_nif'
            )
        ]

# products/models.py
class Product(models.Model):
    name = models.CharField(max_length=200)
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Número de série do produto'
    )
    # ... other fields ...
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['serial_number'],
                condition=models.Q(serial_number__isnull=False),
                name='unique_product_serial'
            )
        ]

# Handle IntegrityError in forms
# customers/forms.py
from django.db import IntegrityError

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
    
    def save(self, commit=True):
        try:
            return super().save(commit=commit)
        except IntegrityError as e:
            if 'unique_customer_nif' in str(e):
                raise ValidationError({
                    'nif': 'Já existe um cliente com este NIF'
                })
            raise
```

**Constraint Features**:
- Unique only when not null (partial unique index)
- Database-level enforcement
- Race condition protection
- Graceful error handling in forms

**Files to Modify**:
- `customers/models.py`: Add unique constraint
- `suppliers/models.py`: Add unique constraint
- `products/models.py`: Add unique constraint
- `customers/forms.py`: Handle IntegrityError
- `suppliers/forms.py`: Handle IntegrityError
- `products/forms.py`: Handle IntegrityError
- Nova migration para adicionar constraints


### Requirement 25: Celery Task Queue for Async Operations

**Design Pattern**: Celery with Redis Backend

**Implementation**:

```python
# app/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('sge')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'backup-database-daily': {
        'task': 'app.tasks.backup_database',
        'schedule': crontab(hour=2, minute=0),
    },
}

# app/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)

# app/settings.py
# Celery Configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Luanda'
CELERY_RESULT_EXPIRES = 86400  # 24 hours

# reports/tasks.py
from celery import shared_task
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_excel_report(self, report_type, filters, user_email):
    """Generate Excel report in background"""
    try:
        # Generate report
        filename = create_excel_report(report_type, filters)
        
        # Send email with download link
        send_mail(
            subject='Relatório Excel Pronto',
            message=f'O seu relatório está pronto para download: {filename}',
            from_email='noreply@sge.ao',
            recipient_list=[user_email],
        )
        
        return f'Report generated: {filename}'
        
    except Exception as e:
        logger.error(f'Report generation failed: {e}')
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=3)
def generate_pdf_report(self, report_type, filters, user_email):
    """Generate PDF report in background"""
    try:
        filename = create_pdf_report(report_type, filters)
        
        send_mail(
            subject='Relatório PDF Pronto',
            message=f'O seu relatório está pronto para download: {filename}',
            from_email='noreply@sge.ao',
            recipient_list=[user_email],
        )
        
        return f'Report generated: {filename}'
        
    except Exception as e:
        logger.error(f'Report generation failed: {e}')
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

# reports/views.py
from reports.tasks import generate_excel_report, generate_pdf_report

class ReportExportView(View):
    def post(self, request):
        report_type = request.POST.get('report_type')
        export_format = request.POST.get('format')
        filters = self.get_filters()
        
        if export_format == 'excel':
            task = generate_excel_report.delay(
                report_type, filters, request.user.email
            )
        elif export_format == 'pdf':
            task = generate_pdf_report.delay(
                report_type, filters, request.user.email
            )
        
        messages.info(
            request,
            f'Relatório em processamento. Receberá email quando concluído. '
            f'Task ID: {task.id}'
        )
        
        return redirect('reports:task_status', task_id=task.id)

class TaskStatusView(View):
    """Check task status"""
    
    def get(self, request, task_id):
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        return JsonResponse({
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None
        })
```

**Celery Setup Commands**:

```bash
# Start Celery worker
celery -A app worker -l info

# Start Celery Beat (scheduler)
celery -A app beat -l info

# Monitor with Flower (optional)
celery -A app flower
```

**Files to Create/Modify**:
- `app/celery.py`: NEW - Celery app configuration
- `app/__init__.py`: Import celery app
- `app/tasks.py`: Backup task (já criado em Req 13)
- `reports/tasks.py`: NEW - Report generation tasks
- `reports/views.py`: Task dispatch and status views
- `app/settings.py`: Celery configuration
- `requirements.txt`: celery, redis
- `.env.example`: REDIS_URL


### Requirement 26: Advanced Report Filters

**Design Pattern**: FilterSet with URL Query String Persistence

**Implementation**:

```python
# reports/filters.py
import django_filters
from django import forms

class BaseReportFilter(django_filters.FilterSet):
    """Base filter for all reports"""
    
    start_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Data Inicial'
    )
    
    end_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Data Final'
    )

class OutflowReportFilter(BaseReportFilter):
    """Filter for outflow reports"""
    
    customer = django_filters.ModelChoiceFilter(
        queryset=Customer.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Cliente'
    )
    
    status = django_filters.ChoiceFilter(
        choices=Outflow.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Estado'
    )
    
    class Meta:
        model = Outflow
        fields = ['start_date', 'end_date', 'customer', 'status']

class InflowReportFilter(BaseReportFilter):
    """Filter for inflow reports"""
    
    supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Fornecedor'
    )
    
    class Meta:
        model = Inflow
        fields = ['start_date', 'end_date', 'supplier']

class PaymentReportFilter(BaseReportFilter):
    """Filter for payment reports"""
    
    payment_method = django_filters.ChoiceFilter(
        choices=Payment.METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Método de Pagamento'
    )
    
    class Meta:
        model = Payment
        fields = ['start_date', 'end_date', 'payment_method']

class StockReportFilter(django_filters.FilterSet):
    """Filter for stock reports"""
    
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Categoria'
    )
    
    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Apenas Stock Baixo'
    )
    
    class Meta:
        model = Product
        fields = ['category', 'low_stock']
    
    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity__lt=10)
        return queryset

# reports/views.py
from django_filters.views import FilterView

class OutflowReportView(FilterView):
    """Outflow report with advanced filters"""
    
    model = Outflow
    filterset_class = OutflowReportFilter
    template_name = 'reports/outflow_report.html'
    paginate_by = 50
    
    def get_queryset(self):
        return Outflow.objects.select_related(
            'customer', 'product'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add active filters for display
        context['active_filters'] = self.get_active_filters()
        
        # Add clear filters URL
        context['clear_url'] = self.request.path
        
        return context
    
    def get_active_filters(self):
        """Get active filters for display"""
        filters = {}
        for key, value in self.request.GET.items():
            if key not in ['page', 'format'] and value:
                filters[key] = value
        return filters
```

**Template Integration**:

```html
<!-- reports/templates/reports/outflow_report.html -->
<form method="get" class="filter-form">
    {{ filter.form.as_p }}
    <button type="submit" class="btn btn-primary">Filtrar</button>
    {% if active_filters %}
        <a href="{{ clear_url }}" class="btn btn-secondary">Limpar Filtros</a>
    {% endif %}
</form>

{% if active_filters %}
<div class="active-filters">
    <h5>Filtros Ativos:</h5>
    <ul>
    {% for key, value in active_filters.items %}
        <li>{{ key }}: {{ value }}</li>
    {% endfor %}
    </ul>
</div>
{% endif %}

<table class="table">
    {% for outflow in object_list %}
    <tr>
        <td>{{ outflow.customer }}</td>
        <td>{{ outflow.product }}</td>
        <td>{{ outflow.quantity }}</td>
        <td>{{ outflow.status }}</td>
    </tr>
    {% endfor %}
</table>
```

**Key Features**:
- URL query string persistence (bookmarkable)
- Multiple filter combination (AND logic)
- Clear filters button
- Active filters display
- Performance: < 2s for 10k records

**Files to Create/Modify**:
- `requirements.txt`: django-filter
- `reports/filters.py`: NEW - Filter classes
- `reports/views.py`: Use FilterView
- `reports/templates/`: Update templates with filters
- `app/settings.py`: Add django_filters to INSTALLED_APPS


### Requirement 27: Parser and Serializer for Configuration

**Design Pattern**: JSON Schema Validation with Dataclasses

**Implementation**:

```python
# app/config_parser.py
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path

@dataclass
class CompanyInfo:
    name: str
    address: str
    phone: str
    email: str
    nif: str

@dataclass
class DatabaseConfig:
    engine: str
    name: str
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None

@dataclass
class CacheConfig:
    backend: str
    location: str
    timeout: int = 300

@dataclass
class LoggingConfig:
    level: str
    max_bytes: int
    backup_count: int

@dataclass
class Configuration:
    company_info: CompanyInfo
    database: DatabaseConfig
    cache: CacheConfig
    logging: LoggingConfig

class ConfigParser:
    """Parse and validate configuration files"""
    
    REQUIRED_FIELDS = ['COMPANY_INFO', 'DATABASE', 'CACHE', 'LOGGING']
    
    @staticmethod
    def parse(config_path: Path) -> Configuration:
        """
        Parse JSON configuration file into Configuration object
        
        Args:
            config_path: Path to JSON configuration file
            
        Returns:
            Configuration object
            
        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is malformed
        """
        if not config_path.exists():
            raise FileNotFoundError(f'Configuration file not found: {config_path}')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON at line {e.lineno}: {e.msg}')
        
        # Validate required fields
        ConfigParser._validate_required_fields(data)
        
        # Parse sections
        try:
            company_info = CompanyInfo(**data['COMPANY_INFO'])
            database = DatabaseConfig(**data['DATABASE'])
            cache = CacheConfig(**data['CACHE'])
            logging = LoggingConfig(**data['LOGGING'])
            
            return Configuration(
                company_info=company_info,
                database=database,
                cache=cache,
                logging=logging
            )
        except TypeError as e:
            raise ValueError(f'Invalid configuration structure: {e}')
    
    @staticmethod
    def _validate_required_fields(data: Dict[str, Any]):
        """Validate required top-level fields"""
        missing = [f for f in ConfigParser.REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValueError(f'Missing required fields: {", ".join(missing)}')
    
    @staticmethod
    def validate_types(config: Configuration) -> bool:
        """
        Validate field types match expected schema
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        # Company Info validation
        if not isinstance(config.company_info.name, str):
            raise ValueError('COMPANY_INFO.name must be string')
        
        # Database validation
        if config.database.engine not in ['sqlite3', 'postgresql', 'mysql']:
            raise ValueError(f'Invalid database engine: {config.database.engine}')
        
        # Cache validation
        if not isinstance(config.cache.timeout, int) or config.cache.timeout < 0:
            raise ValueError('CACHE.timeout must be positive integer')
        
        # Logging validation
        if config.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            raise ValueError(f'Invalid logging level: {config.logging.level}')
        
        return True

class ConfigPrettyPrinter:
    """Format Configuration objects back to JSON"""
    
    @staticmethod
    def to_json(config: Configuration, indent: int = 2) -> str:
        """
        Convert Configuration object to formatted JSON string
        
        Args:
            config: Configuration object
            indent: Number of spaces for indentation
            
        Returns:
            Formatted JSON string
        """
        data = {
            'COMPANY_INFO': asdict(config.company_info),
            'DATABASE': asdict(config.database),
            'CACHE': asdict(config.cache),
            'LOGGING': asdict(config.logging),
        }
        
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def to_file(config: Configuration, output_path: Path, indent: int = 2):
        """
        Write Configuration object to JSON file
        
        Args:
            config: Configuration object
            output_path: Path to output file
            indent: Number of spaces for indentation
        """
        json_str = ConfigPrettyPrinter.to_json(config, indent)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

# app/management/commands/load_config.py
from django.core.management.base import BaseCommand
from app.config_parser import ConfigParser
from pathlib import Path

class Command(BaseCommand):
    help = 'Load configuration from JSON file'
    
    def add_arguments(self, parser):
        parser.add_argument('config_file', type=str, help='Path to config JSON file')
    
    def handle(self, *args, **options):
        config_path = Path(options['config_file'])
        
        try:
            config = ConfigParser.parse(config_path)
            ConfigParser.validate_types(config)
            
            # Apply to Django settings
            self.apply_config(config)
            
            self.stdout.write(
                self.style.SUCCESS(f'Configuration loaded from {config_path}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to load configuration: {e}')
            )
    
    def apply_config(self, config):
        """Apply configuration to Django settings"""
        from django.conf import settings
        
        # Update settings (in production, this would update environment variables)
        settings.COMPANY_NAME = config.company_info.name
        settings.COMPANY_EMAIL = config.company_info.email
        # ... apply other settings
```

**Example Configuration File**:

```json
{
  "COMPANY_INFO": {
    "name": "SGE - Sistema de Gestão de Stocks",
    "address": "Luanda, Angola",
    "phone": "+244 900 000 000",
    "email": "info@sge.ao",
    "nif": "123456789"
  },
  "DATABASE": {
    "engine": "sqlite3",
    "name": "db.sqlite3"
  },
  "CACHE": {
    "backend": "redis",
    "location": "redis://localhost:6379/1",
    "timeout": 300
  },
  "LOGGING": {
    "level": "INFO",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

**Key Features**:
- JSON schema validation
- Type checking
- Descriptive error messages with line numbers
- Round-trip property (parse → print → parse)
- Django management command for loading

**Files to Create**:
- `app/config_parser.py`: NEW - Parser and printer
- `app/management/commands/load_config.py`: NEW - Management command
- `config.example.json`: NEW - Example configuration


## Implementation Strategy

### Phase 1: P0 - Critical Security and Data Integrity (Week 1-2)

**Priority**: Immediate implementation required

**Requirements**: 1-6
- Concurrency control in stock operations
- Negative quantity validation
- Atomic delivery deletion
- Dashboard cache invalidation
- Authentication rate limiting
- CSRF protection for AJAX

**Rationale**: These address critical security vulnerabilities and data integrity issues that could cause data loss or security breaches.

**Testing**: Focus on concurrency tests, validation tests, and security tests.

### Phase 2: P1 - Important Performance and Validation (Week 3-5)

**Priority**: High - Complete within 1 month

**Requirements**: 7-18
- Query optimization
- Database indexes
- Email and NIF validation
- Log rotation
- Sentry integration
- Database backups
- Payment date validation
- Thread-local cleanup
- Paginated exports
- Permission validation
- Exception handling in audit

**Rationale**: These improve system performance, reliability, and operational quality.

**Testing**: Performance benchmarks, integration tests, load tests.

### Phase 3: P2-P3 - Quality and Feature Improvements (Week 6-12)

**Priority**: Medium - Complete within 3 months

**Requirements**: 19-27
- Test coverage improvement
- Integration test suite
- Code refactoring
- File upload validation
- Soft delete
- Uniqueness constraints
- Celery task queue
- Advanced filters
- Configuration parser

**Rationale**: These enhance code quality, maintainability, and user experience.

**Testing**: Comprehensive test suite, refactoring validation.


## Dependencies and Infrastructure

### New Python Packages

```txt
# requirements.txt additions

# Security and Rate Limiting
django-ratelimit==4.1.0

# Monitoring
sentry-sdk==1.40.0

# Task Queue
celery==5.3.4
redis==5.0.1

# Filtering
django-filter==23.5

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
coverage==7.4.0
```

### Infrastructure Requirements

**Redis Server**:
- Purpose: Celery broker, cache backend, rate limiting
- Installation: `sudo apt-get install redis-server` (Linux) or Docker
- Configuration: Default localhost:6379

**Celery Workers**:
- Worker process: `celery -A app worker -l info`
- Beat scheduler: `celery -A app beat -l info`
- Monitoring: `celery -A app flower` (optional)

**Sentry Account**:
- Sign up at sentry.io
- Create project
- Get DSN for SENTRY_DSN environment variable

### Environment Variables

```bash
# .env additions

# Sentry
SENTRY_DSN=https://your-key@sentry.io/project-id
APP_VERSION=1.0.0

# Redis
REDIS_URL=redis://localhost:6379/0

# Backups
BACKUP_DIR=/path/to/backups

# Email (for task notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=True
```


## Database Migrations Strategy

### Migration Order

1. **Add validation fields** (Req 2, 9, 10):
   - Add CheckConstraints for non-negative quantities
   - Update email and NIF validators

2. **Add indexes** (Req 7, 8):
   - Composite indexes on frequently queried columns
   - Single-column indexes for foreign keys

3. **Add uniqueness constraints** (Req 24):
   - Unique constraints on NIF and serial_number (with null condition)

4. **Add soft delete fields** (Req 23):
   - is_deleted, deleted_at fields to Delivery model

5. **Data migration** (if needed):
   - Clean up any existing invalid data before applying constraints

### Migration Commands

```bash
# Generate migrations
python manage.py makemigrations

# Review migrations
python manage.py sqlmigrate app_name migration_number

# Apply migrations
python manage.py migrate

# Rollback if needed
python manage.py migrate app_name previous_migration
```

### Backward Compatibility

- All new fields are nullable or have defaults
- Constraints are added after data cleanup
- Soft delete doesn't break existing queries (manager filters)
- Indexes are additive (don't break existing queries)


## Testing Strategy

### Unit Tests

**Coverage Target**: 80%+ overall

**Test Categories**:
1. **Model Tests**:
   - Field validation
   - Custom methods
   - Properties
   - Constraints

2. **Form Tests**:
   - Valid data acceptance
   - Invalid data rejection
   - Custom clean methods
   - Error messages

3. **View Tests**:
   - HTTP status codes
   - Template usage
   - Context data
   - Permissions

4. **Utility Tests**:
   - Validators
   - Helpers
   - Middleware
   - Signals

### Integration Tests

**Test Scenarios**:
1. Complete outflow workflow
2. Payment and reconciliation
3. Inflow and stock update
4. Authentication and authorization
5. Report generation

**Performance Target**: < 5 minutes for full suite

### Concurrency Tests

**Critical Tests**:
1. Concurrent stock updates (Req 1)
2. Race condition on unique constraints (Req 24)
3. Concurrent delivery deletions (Req 3)

**Implementation**:
```python
from threading import Thread
from django.test import TransactionTestCase

class ConcurrencyTests(TransactionTestCase):
    def test_concurrent_stock_updates(self):
        """Test that concurrent updates maintain consistency"""
        product = Product.objects.create(quantity=100)
        
        def decrement_stock():
            with transaction.atomic():
                p = Product.objects.select_for_update().get(pk=product.pk)
                p.quantity -= 10
                p.save()
        
        # Run 10 concurrent decrements
        threads = [Thread(target=decrement_stock) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify final quantity
        product.refresh_from_db()
        self.assertEqual(product.quantity, 0)  # 100 - (10 * 10)
```

### Performance Tests

**Benchmarks**:
1. Query optimization (Req 7): < 3 queries for balance views
2. Index performance (Req 8): 50%+ improvement on 1000+ records
3. Export performance (Req 16): Constant memory usage
4. Report filters (Req 26): < 2s for 10k records


## Risk Assessment and Mitigation

### Technical Risks

**Risk 1: Redis Dependency**
- **Impact**: High - Celery and caching depend on Redis
- **Probability**: Low
- **Mitigation**: 
  - Graceful degradation if Redis unavailable
  - Fallback to database cache backend
  - Clear documentation for Redis setup

**Risk 2: Migration Failures**
- **Impact**: High - Could break production
- **Probability**: Medium
- **Mitigation**:
  - Test migrations on copy of production database
  - Backup before migration
  - Rollback plan for each migration
  - Staged rollout (dev → staging → production)

**Risk 3: Performance Degradation from Locking**
- **Impact**: Medium - select_for_update could cause bottlenecks
- **Probability**: Low
- **Mitigation**:
  - Lock timeout configuration
  - Monitor lock wait times
  - Optimize transaction duration
  - Consider optimistic locking for high-contention scenarios

**Risk 4: Test Suite Execution Time**
- **Impact**: Low - Slow tests reduce developer productivity
- **Probability**: Medium
- **Mitigation**:
  - Parallel test execution
  - Fast test subset for quick feedback
  - Full suite in CI/CD only

### Operational Risks

**Risk 5: Celery Worker Downtime**
- **Impact**: Medium - Background tasks won't execute
- **Probability**: Medium
- **Mitigation**:
  - Process monitoring (systemd, supervisor)
  - Auto-restart on failure
  - Task retry logic
  - Alerting on worker failure

**Risk 6: Disk Space from Logs and Backups**
- **Impact**: Low - Could fill disk
- **Probability**: Low
- **Mitigation**:
  - Log rotation (10MB × 5 files = 50MB max)
  - Backup rotation (30 days)
  - Disk space monitoring
  - Alerts at 80% capacity


## Monitoring and Observability

### Key Metrics

**Application Metrics**:
- Request rate and response time
- Error rate by endpoint
- Database query count and duration
- Cache hit/miss ratio
- Celery task queue length
- Celery task execution time

**Business Metrics**:
- Stock operations per hour
- Failed login attempts
- Rate limit violations
- Audit log entries created
- Export operations initiated

**Infrastructure Metrics**:
- Redis memory usage
- Database size
- Disk space usage
- Log file sizes
- Backup success/failure rate

### Alerting Rules

**Critical Alerts** (immediate action):
- Database backup failure
- Sentry error rate > 10/minute
- Redis connection failure
- Disk space > 90%

**Warning Alerts** (investigate within 24h):
- Cache hit ratio < 50%
- Celery queue length > 100
- Average response time > 2s
- Failed login attempts > 50/hour

### Logging Strategy

**Log Levels**:
- **DEBUG**: Development only
- **INFO**: Normal operations (backups, task completion)
- **WARNING**: Recoverable issues (rate limits, validation failures)
- **ERROR**: Failures requiring attention (backup failures, task failures)

**Structured Logging**:
```python
logger.info('Stock updated', extra={
    'product_id': product.id,
    'old_quantity': old_qty,
    'new_quantity': new_qty,
    'user': request.user.username
})
```


## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (unit + integration)
- [ ] Code coverage ≥ 80%
- [ ] Database backup created
- [ ] Redis server installed and running
- [ ] Environment variables configured
- [ ] Sentry project created and DSN obtained
- [ ] Migration plan reviewed
- [ ] Rollback plan documented

### Deployment Steps

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

3. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Collect Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Start Celery Workers**:
   ```bash
   celery -A app worker -l info --detach
   celery -A app beat -l info --detach
   ```

6. **Restart Application**:
   ```bash
   systemctl restart gunicorn
   # or your application server
   ```

### Post-Deployment

- [ ] Verify application is accessible
- [ ] Check Sentry for errors
- [ ] Verify Celery workers are running
- [ ] Test critical workflows (login, stock update, report generation)
- [ ] Monitor logs for errors
- [ ] Verify backup task scheduled
- [ ] Check Redis connection
- [ ] Monitor performance metrics

### Rollback Procedure

If issues occur:

1. **Stop Celery Workers**:
   ```bash
   pkill -f "celery worker"
   ```

2. **Rollback Migrations**:
   ```bash
   python manage.py migrate app_name previous_migration
   ```

3. **Restore Database Backup**:
   ```bash
   cp backups/db_backup_TIMESTAMP.sqlite3 db.sqlite3
   ```

4. **Revert Code**:
   ```bash
   git checkout previous_version
   ```

5. **Restart Application**


## File Structure Summary

### New Files to Create

```
app/
├── cache_utils.py          # Cache invalidation utilities
├── validators.py           # Custom validators (NIF, file content)
├── celery.py              # Celery configuration
├── tasks.py               # Celery tasks (backup)
├── config_parser.py       # Configuration parser
├── models.py              # SoftDeleteModel base class
├── static/
│   └── js/
│       └── csrf.js        # CSRF token handling
└── management/
    └── commands/
        └── load_config.py # Load configuration command

reports/
├── base.py                # Base report views
├── filters.py             # Report filters
├── tasks.py               # Report generation tasks
└── mixins.py              # Reusable mixins

tests/
└── integration/
    ├── __init__.py
    ├── test_outflow_workflow.py
    ├── test_payment_workflow.py
    ├── test_inflow_workflow.py
    ├── test_auth_workflow.py
    └── test_reports.py

products/
├── signals.py             # Cache invalidation signals
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    └── test_forms.py

# Similar test structure for other apps

config.example.json        # Example configuration file
pytest.ini                 # Pytest configuration
```

### Files to Modify

**Settings and Configuration**:
- `app/settings.py`: Logging, Celery, Sentry, cache configuration
- `app/__init__.py`: Import Celery app
- `requirements.txt`: Add new dependencies
- `.env.example`: Add new environment variables

**Models** (add validation, constraints, indexes):
- `products/models.py`
- `customers/models.py`
- `suppliers/models.py`
- `inflows/models.py`
- `outflows/models.py`
- `payments/models.py`
- `accounts/models.py`

**Forms** (add validation):
- `products/forms.py`
- `customers/forms.py`
- `suppliers/forms.py`
- `inflows/forms.py`
- `outflows/forms.py`
- `payments/forms.py`

**Views** (add concurrency control, optimization, filters):
- `products/views.py`
- `outflows/views.py`
- `accounts/views.py`
- `reports/views.py`
- `users/views.py`
- `app/views.py`

**Signals** (add cache invalidation, exception handling):
- `inflows/signals.py`
- `outflows/signals.py`
- `payments/signals.py`
- `accounts/signals.py`
- `audit/signals.py`

**Middleware**:
- `audit/middleware.py`: Thread-local cleanup

**Templates**:
- `app/templates/base.html`: Include CSRF script
- `reports/templates/`: Add filter forms

**Admin**:
- All `admin.py` files: Add BulkDeleteMixin


## Success Criteria

### Functional Requirements

- [ ] All 27 requirements implemented and tested
- [ ] All existing 93 tests still passing
- [ ] New tests added for all new functionality
- [ ] Code coverage ≥ 80%

### Performance Requirements

- [ ] Balance views execute in ≤ 3 database queries
- [ ] Indexed queries 50%+ faster on 1000+ records
- [ ] Export operations use constant memory
- [ ] Report filters return results in < 2s for 10k records

### Security Requirements

- [ ] Rate limiting active on login endpoint
- [ ] CSRF protection on all AJAX requests
- [ ] File uploads validated by content
- [ ] Unique constraints enforced at database level
- [ ] Permissions validated on bulk operations

### Reliability Requirements

- [ ] Database backups running daily
- [ ] Log rotation configured (10MB × 5 files)
- [ ] Sentry capturing errors
- [ ] Audit logging resilient to failures
- [ ] Thread-local storage cleaned up properly

### Quality Requirements

- [ ] Code duplication reduced by 40%+ in reports
- [ ] All validation at form and database level
- [ ] Comprehensive integration test suite
- [ ] Configuration parser with validation
- [ ] Soft delete for Delivery model

## Conclusion

Este design fornece uma solução completa e detalhada para os 27 requisitos de melhorias e hardening do sistema SGE. A implementação está organizada em 3 fases por prioridade, com estratégias claras de teste, deployment e monitoramento.

**Principais Benefícios**:
- **Segurança**: Rate limiting, CSRF protection, file validation
- **Integridade**: Concurrency control, atomic transactions, constraints
- **Performance**: Query optimization, indexes, caching, async tasks
- **Confiabilidade**: Backups automáticos, error monitoring, log rotation
- **Qualidade**: 80%+ test coverage, code refactoring, comprehensive tests
- **Operabilidade**: Celery tasks, advanced filters, configuration management

A implementação seguirá as melhores práticas Django, mantendo compatibilidade com o código existente e garantindo que todos os 93 testes atuais continuem a passar.
