from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from brands.models import Brand
from categories.models import Category
from customers.models import Customer
from suppliers.models import Supplier
from products.models import Product
from inflows.models import Inflow
from outflows.models import Outflow, Delivery
from drivers.models import Driver


class FullWorkflowTest(TestCase):
    """Test complete product lifecycle: inflow -> outflow -> delivery."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='TestBrand')
        cls.category = Category.objects.create(name='TestCategory')
        cls.customer = Customer.objects.create(name='TestCustomer')
        cls.supplier = Supplier.objects.create(name='TestSupplier')
        cls.driver = Driver.objects.create(
            name='TestDriver', phone='+244911111111',
            truck_plate='AB-12-34-CD', cistern_plate='EF-56-78-GH',
        )
        cls.product = Product.objects.create(
            title='TestProduct', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('20.00'),
            quantity=Decimal('0'),
        )

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        self.client.force_login(self.user)

    def test_full_inflow_outflow_delivery_cycle(self):
        # 1. Create inflow to increase stock
        initial_qty = self.product.quantity
        inflow = Inflow.objects.create(
            product=self.product, supplier=self.supplier,
            quantity=Decimal('100'), price=Decimal('10.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, initial_qty + Decimal('100'))

        # 2. Create outflow (stock unchanged — only delivery reduces stock)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('30'), price=Decimal('20.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))

        # 3. Create delivery — stock decreases by final_quantity (20)
        delivery = Delivery.objects.create(
            outflow=outflow, quantity=Decimal('20'), driver=self.driver,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('80'))

        # 4. Confirm delivery with different actual_quantity — stock adjusts
        delivery.actual_quantity = Decimal('18')
        delivery.is_confirmed = True
        delivery.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('82'))

        # 5. Soft-delete delivery — stock is restored
        delivery.delete()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))
