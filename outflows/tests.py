"""Tests for outflow views: delivery, trash, shipping guide, confirm weight."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from drivers.models import Driver
from outflows.models import Outflow, Delivery


class OutflowViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.brand = Brand.objects.create(name='Brand')
        cls.category = Category.objects.create(name='Cat')
        cls.customer = Customer.objects.create(name='Customer')
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'),
            quantity=Decimal('100'),
        )
        cls.driver = Driver.objects.create(name='Driver', phone='123456789')
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('20'), price=Decimal('15.00'),
        )

    def test_outflow_list(self):
        self.client.force_login(self.user)
        response = self.client.get('/outflows/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product')

    def test_outflow_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/outflows/{self.outflow.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product')

    def test_outflow_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get('/outflows/create/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post('/outflows/create/', {
            'product': self.product.pk,
            'customer': self.customer.pk,
            'quantity': '10',
            'price': '15.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Outflow.objects.filter(quantity=Decimal('10')).exists())

    def test_outflow_update_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/outflows/{self.outflow.pk}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_delete_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/outflows/{self.outflow.pk}/delete/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_soft_delete(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/outflows/{self.outflow.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.outflow.refresh_from_db()
        self.assertTrue(self.outflow.is_deleted)

    def test_outflow_trash_list(self):
        self.client.force_login(self.user)
        self.outflow.delete()
        response = self.client.get('/outflows/trash/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_restore(self):
        self.client.force_login(self.user)
        self.outflow.delete()
        response = self.client.post(f'/outflows/{self.outflow.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.outflow.refresh_from_db()
        self.assertFalse(self.outflow.is_deleted)

    def test_outflow_hard_delete(self):
        self.client.force_login(self.user)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('5'), price=Decimal('10.00'),
        )
        outflow.delete()
        response = self.client.post(f'/outflows/{outflow.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Outflow.all_objects.filter(pk=outflow.pk).exists())

    def test_delivery_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/outflows/{self.outflow.pk}/delivery/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/outflows/{self.outflow.pk}/delivery/', {
            'quantity': '10',
            'driver': self.driver.pk,
            'delivered_at': '2026-05-26',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Delivery.objects.filter(quantity=Decimal('10')).exists())

    def test_delivery_shipping_guide(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('10'),
            driver=self.driver,
        )
        response = self.client.get(f'/deliveries/{delivery.pk}/shipping-guide/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_confirm_weight_get(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('10'),
            driver=self.driver,
        )
        response = self.client.get(f'/deliveries/{delivery.pk}/confirm-weight/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_confirm_weight_post(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('10'),
            driver=self.driver,
        )
        response = self.client.post(f'/deliveries/{delivery.pk}/confirm-weight/', {
            'actual_quantity': '12',
        })
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertTrue(delivery.is_confirmed)
        self.assertEqual(delivery.actual_quantity, Decimal('12'))

    def test_delivery_delete(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=self.driver,
        )
        response = self.client.post(f'/deliveries/{delivery.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertTrue(delivery.is_deleted)

    def test_delivery_trash_list(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=self.driver,
        )
        delivery.delete()
        response = self.client.get('/deliveries/trash/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_restore(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=self.driver,
        )
        delivery.delete()
        response = self.client.post(f'/deliveries/{delivery.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertFalse(delivery.is_deleted)

    def test_delivery_hard_delete(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=self.driver,
        )
        delivery.delete()
        response = self.client.post(f'/deliveries/{delivery.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Delivery.all_objects.filter(pk=delivery.pk).exists())
