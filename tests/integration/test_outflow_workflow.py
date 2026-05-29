from decimal import Decimal
from django.test import TestCase
from products.models import Product
from outflows.models import Outflow, Delivery
from tests.factories import TenantFactory, BrandFactory, CategoryFactory, CustomerFactory, ProductFactory, OutflowFactory, DeliveryFactory


class OutflowWorkflowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='outflow-test')
        cls.brand = BrandFactory(name='B', tenant=cls.tenant)
        cls.category = CategoryFactory(name='C', tenant=cls.tenant)
        cls.customer = CustomerFactory(name='Cliente', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Prod',
            category=cls.category,
            brand=cls.brand,
            tenant=cls.tenant,
        )

    def test_outflow_and_delivery_soft_delete(self):
        outflow = OutflowFactory(
            product=self.product,
            customer=self.customer,
            quantity=Decimal('10'),
            tenant=self.tenant,
        )
        delivery = DeliveryFactory(
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
