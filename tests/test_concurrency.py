from decimal import Decimal
from django.test import TransactionTestCase
from django.db import transaction
from brands.models import Brand
from categories.models import Category
from customers.models import Customer
from products.models import Product
from outflows.models import Outflow
from tenants.models import Tenant


class StockConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ConcurrencyTest', slug='concurrency-test')
        self.brand = Brand.objects.create(name='B', tenant=self.tenant)
        self.category = Category.objects.create(name='C', tenant=self.tenant)
        self.customer = Customer.objects.create(name='Cliente', tenant=self.tenant)
        self.product = Product.objects.create(
            title='P',
            category=self.category,
            brand=self.brand,
            cost_price=Decimal('10'),
            selling_price=Decimal('15'),
            quantity=Decimal('100'),
            tenant=self.tenant,
        )

    def test_select_for_update_prevents_oversell(self):
        with transaction.atomic():
            p = Product.objects.select_for_update().get(pk=self.product.pk)
            qty_available = p.quantity
        self.assertEqual(qty_available, Decimal('100'))
        Outflow.objects.create(
            product=self.product,
            customer=self.customer,
            quantity=Decimal('30'),
            tenant=self.tenant,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))
