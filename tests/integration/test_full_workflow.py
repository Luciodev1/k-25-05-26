from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from products.models import Product
from outflows.models import Outflow, Delivery
from tenants.models import TenantUser
from tests.factories import TenantFactory, BrandFactory, CategoryFactory, CustomerFactory, SupplierFactory, DriverFactory, ProductFactory, InflowFactory, OutflowFactory, DeliveryFactory


class FullWorkflowTest(TestCase):
    """Test complete product lifecycle: inflow -> outflow -> delivery."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='workflow-test')
        cls.brand = BrandFactory(name='TestBrand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='TestCategory', tenant=cls.tenant)
        cls.customer = CustomerFactory(name='TestCustomer', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='TestSupplier', tenant=cls.tenant)
        cls.driver = DriverFactory(
            name='TestDriver', phone='+244 923 000 000',
            truck_plate='LD-01-AA-00', cistern_plate='LD-01-BB-00',
            tenant=cls.tenant,
        )
        cls.product = ProductFactory(
            title='TestProduct', category=cls.category, brand=cls.brand,
            tenant=cls.tenant,
        )
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')
        cls.product_zero = ProductFactory(
            title='ZeroProduct', category=cls.category, brand=cls.brand,
            quantity=Decimal('0'), tenant=cls.tenant,
        )

    def test_full_inventory_workflow(self):
        inflow = InflowFactory(
            product=self.product, supplier=self.supplier,
            quantity=Decimal('50'), price=Decimal('10.00'), tenant=self.tenant,
        )
        outflow = OutflowFactory(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'), tenant=self.tenant,
        )
        delivery = DeliveryFactory(
            outflow=outflow, quantity=Decimal('10'),
            driver=self.driver, tenant=self.tenant,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_full_inflow_outflow_delivery_cycle(self):
        # 1. Create inflow to increase stock
        initial_qty = self.product_zero.quantity
        inflow = InflowFactory(
            product=self.product_zero, supplier=self.supplier,
            quantity=Decimal('100'), price=Decimal('10.00'), tenant=self.tenant,
        )
        self.product_zero.refresh_from_db()
        self.assertEqual(self.product_zero.quantity, initial_qty + Decimal('100'))

        # 2. Create outflow (stock unchanged — only delivery reduces stock)
        outflow = OutflowFactory(
            product=self.product_zero, customer=self.customer,
            quantity=Decimal('30'), price=Decimal('20.00'), tenant=self.tenant,
        )
        self.product_zero.refresh_from_db()
        self.assertEqual(self.product_zero.quantity, Decimal('100'))

        # 3. Create delivery — stock decreases by final_quantity (20)
        delivery = DeliveryFactory(
            outflow=outflow, quantity=Decimal('20'), driver=self.driver,
            tenant=self.tenant,
        )
        self.product_zero.refresh_from_db()
        self.assertEqual(self.product_zero.quantity, Decimal('80'))

        # 4. Confirm delivery with different actual_quantity — stock adjusts
        delivery.actual_quantity = Decimal('18')
        delivery.is_confirmed = True
        delivery.save()
        self.product_zero.refresh_from_db()
        self.assertEqual(self.product_zero.quantity, Decimal('82'))

        # 5. Soft-delete delivery — stock is restored
        delivery.delete()
        self.product_zero.refresh_from_db()
        self.assertEqual(self.product_zero.quantity, Decimal('100'))
