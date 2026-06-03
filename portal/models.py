from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer
from app.mixins import SoftDeleteModel


class CustomerAccess(SoftDeleteModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_access')
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='portal_access')
    is_active = models.BooleanField(default=True, verbose_name='Acesso Ativo')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Último Acesso')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Acesso do Cliente'
        verbose_name_plural = 'Acessos dos Clientes'

    def __str__(self):
        return f'{self.customer.name} - {self.user.username}'
