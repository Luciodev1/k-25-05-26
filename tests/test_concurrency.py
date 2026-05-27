from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from brands.models import Brand
from categories.models import Category
from customers.models import Customer
from products.models import Product
from outflows.models import Outflow


class StockConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='B')
        self.category = Category.objects.create(name='C')
        self.customer = Customer.objects.create(name='Cliente')
        self.product = Product.objects.create(
            title='P',
            category=self.category,
            brand=self.brand,
            cost_price=Decimal('10'),
            selling_price=Decimal('15'),
            quantity=Decimal('100'),
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
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))
