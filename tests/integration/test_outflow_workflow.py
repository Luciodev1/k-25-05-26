from decimal import Decimal
from django.test import TestCase
from brands.models import Brand
from categories.models import Category
from customers.models import Customer
from products.models import Product
from outflows.models import Outflow, Delivery
from tenants.models import Tenant


class OutflowWorkflowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='OutflowTest', slug='outflow-test')
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.category = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cliente', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='Prod',
            category=cls.category,
            brand=cls.brand,
            cost_price=Decimal('10'),
            selling_price=Decimal('20'),
            quantity=Decimal('50'),
            tenant=cls.tenant,
        )

    def test_outflow_and_delivery_soft_delete(self):
        outflow = Outflow.objects.create(
            product=self.product,
            customer=self.customer,
            quantity=Decimal('10'),
            tenant=self.tenant,
        )
        delivery = Delivery.objects.create(
            outflow=outflow,
            quantity=Decimal('5'),
            tenant=self.tenant,
        )
        self.product.refresh_from_db()
        stock_after_delivery = self.product.quantity
        delivery.delete()
        self.product.refresh_from_db()
        self.assertTrue(delivery.is_deleted)
        self.assertEqual(self.product.quantity, stock_after_delivery + Decimal('5'))
