"""Tests for inflow views and signals."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from brands.models import Brand
from categories.models import Category
from products.models import Product
from suppliers.models import Supplier
from inflows.models import Inflow


class InflowSignalTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='Brand')
        cls.category = Category.objects.create(name='Cat')
        cls.supplier = Supplier.objects.create(name='Supplier')
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'),
            quantity=Decimal('100'),
        )

    def test_inflow_increases_stock(self):
        self.assertEqual(self.product.quantity, Decimal('100'))
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('50'), price=Decimal('10.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('150'))

    def test_inflow_delete_decreases_stock(self):
        inflow = Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('30'), price=Decimal('10.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('130'))
        inflow.delete()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))

    def test_multiple_inflows_accumulate(self):
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('10'), price=Decimal('10.00'),
        )
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10.00'),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('130'))


class InflowViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.brand = Brand.objects.create(name='Brand')
        cls.category = Category.objects.create(name='Cat')
        cls.supplier = Supplier.objects.create(name='Supplier')
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'),
            quantity=Decimal('100'),
        )
        cls.inflow = Inflow.objects.create(
            product=cls.product, supplier=cls.supplier,
            quantity=Decimal('20'), price=Decimal('10.00'),
        )

    def test_inflow_list(self):
        self.client.force_login(self.user)
        response = self.client.get('/inflows/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product')

    def test_inflow_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/inflows/{self.inflow.pk}/detail/')
        self.assertEqual(response.status_code, 200)

    def test_inflow_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get('/inflows/create/')
        self.assertEqual(response.status_code, 200)

    def test_inflow_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post('/inflows/create/', {
            'product': self.product.pk,
            'supplier': self.supplier.pk,
            'quantity': '30',
            'price': '12.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Inflow.objects.filter(quantity=Decimal('30')).exists())

    def test_inflow_update_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/inflows/{self.inflow.pk}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_inflow_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/inflows/{self.inflow.pk}/edit/', {
            'product': self.product.pk,
            'supplier': self.supplier.pk,
            'quantity': '25',
            'price': '11.00',
        })
        self.assertEqual(response.status_code, 302)
        self.inflow.refresh_from_db()
        self.assertEqual(self.inflow.quantity, Decimal('25'))

    def test_inflow_delete_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/inflows/{self.inflow.pk}/delete/')
        self.assertEqual(response.status_code, 200)

    def test_inflow_soft_delete(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/inflows/{self.inflow.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.inflow.refresh_from_db()
        self.assertTrue(self.inflow.is_deleted)

    def test_inflow_trash_list(self):
        self.client.force_login(self.user)
        self.inflow.delete()
        response = self.client.get('/inflows/trash/')
        self.assertEqual(response.status_code, 200)

    def test_inflow_restore(self):
        self.client.force_login(self.user)
        self.inflow.delete()
        response = self.client.post(f'/inflows/{self.inflow.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.inflow.refresh_from_db()
        self.assertFalse(self.inflow.is_deleted)

    def test_inflow_hard_delete(self):
        self.client.force_login(self.user)
        inflow = Inflow.objects.create(
            product=self.product, supplier=self.supplier,
            quantity=Decimal('5'), price=Decimal('10.00'),
        )
        inflow.delete()
        response = self.client.post(f'/inflows/{inflow.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Inflow.all_objects.filter(pk=inflow.pk).exists())
