"""Tests for outflow views: delivery, trash, shipping guide, confirm weight."""
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from django.db.models import ProtectedError
from django.db.models.query import QuerySet
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from drivers.models import Driver
from outflows.models import Outflow, Delivery
from tenants.models import Tenant, TenantUser


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


class OutflowTenantScopedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant)
        cls.other_tenant = Tenant.objects.create(name='Other', slug='other')
        cls.other_admin = User.objects.create_superuser('other', 'o@t.com', 'pass')
        TenantUser.objects.create(user=cls.other_admin, tenant=cls.other_tenant)
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.cat = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.driver = Driver.objects.create(name='Drv', phone='123', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'), quantity=Decimal('50'),
            tenant=cls.tenant,
        )
        cls.other_product = Product.objects.create(
            title='OtherP', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'), quantity=Decimal('50'),
            tenant=cls.other_tenant,
        )
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=cls.tenant,
        )
        cls.delivery = Delivery.objects.create(
            outflow=cls.outflow, quantity=Decimal('5'),
            driver=cls.driver, tenant=cls.tenant,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_outflow_list_tenant_scoped(self):
        response = self.client.get('/outflows/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P')

    def test_outflow_create_with_quantity_exceeds_stock(self):
        response = self.client.post('/outflows/create/', {
            'product': self.product.pk, 'customer': self.customer.pk,
            'quantity': '999', 'price': '15.00',
        })
        self.assertEqual(response.status_code, 200)

    def test_outflow_create_with_default_price(self):
        response = self.client.post('/outflows/create/', {
            'product': self.product.pk, 'customer': self.customer.pk,
            'quantity': '5',
        })
        self.assertEqual(response.status_code, 302)

    def test_outflow_detail(self):
        response = self.client.get(f'/outflows/{self.outflow.pk}/detail/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_update_get(self):
        response = self.client.get(f'/outflows/{self.outflow.pk}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_delete_post(self):
        response = self.client.post(f'/outflows/{self.outflow.pk}/delete/')
        self.assertEqual(response.status_code, 302)

    def test_outflow_trash_list(self):
        self.outflow.delete()
        response = self.client.get('/outflows/trash/')
        self.assertEqual(response.status_code, 200)

    def test_outflow_restore(self):
        self.outflow.delete()
        response = self.client.post(f'/outflows/{self.outflow.pk}/restore/')
        self.assertEqual(response.status_code, 302)

    def test_outflow_hard_delete(self):
        self.outflow.delete()
        response = self.client.post(f'/outflows/{self.outflow.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)

    def test_delivery_create_get(self):
        response = self.client.get(f'/outflows/{self.outflow.pk}/delivery/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_create_post(self):
        response = self.client.post(f'/outflows/{self.outflow.pk}/delivery/', {
            'quantity': '3', 'driver': self.driver.pk,
            'delivered_at': '2026-05-26',
        })
        self.assertEqual(response.status_code, 302)

    def test_delivery_shipping_guide(self):
        response = self.client.get(f'/deliveries/{self.delivery.pk}/shipping-guide/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_confirm_weight_get(self):
        response = self.client.get(f'/deliveries/{self.delivery.pk}/confirm-weight/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_delete_post(self):
        response = self.client.post(f'/deliveries/{self.delivery.pk}/delete/')
        self.assertEqual(response.status_code, 302)

    def test_delivery_trash_list(self):
        self.delivery.delete()
        response = self.client.get('/deliveries/trash/')
        self.assertEqual(response.status_code, 200)

    def test_delivery_restore(self):
        self.delivery.delete()
        response = self.client.post(f'/deliveries/{self.delivery.pk}/restore/')
        self.assertEqual(response.status_code, 302)

    def test_delivery_hard_delete(self):
        self.delivery.delete()
        response = self.client.post(f'/deliveries/{self.delivery.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)

    def test_other_tenant_outflow_detail_404(self):
        self.client.force_login(self.other_admin)
        response = self.client.get(f'/outflows/{self.outflow.pk}/detail/')
        self.assertEqual(response.status_code, 404)


class OutflowUpdateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant)
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.cat = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant,
        )
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=cls.tenant,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_outflow_update_success(self):
        response = self.client.post(
            reverse('outflows:outflow_update', kwargs={'pk': self.outflow.pk}),
            {'product': self.product.pk, 'customer': self.customer.pk,
             'quantity': '15', 'price': '20.00'},
        )
        self.assertRedirects(response, reverse('outflows:outflow_list'))
        self.outflow.refresh_from_db()
        self.assertEqual(self.outflow.quantity, Decimal('15'))
        self.assertEqual(self.outflow.price, Decimal('20.00'))

    def test_outflow_update_stock_exceeds(self):
        response = self.client.post(
            reverse('outflows:outflow_update', kwargs={'pk': self.outflow.pk}),
            {'product': self.product.pk, 'customer': self.customer.pk,
             'quantity': '65', 'price': '15.00'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'excede o estoque')

    def test_outflow_update_product_does_not_exist(self):
        with patch.object(QuerySet, 'select_for_update') as mock_sfu:
            mock_sfu.return_value.get.side_effect = Product.DoesNotExist
            response = self.client.post(
                reverse('outflows:outflow_update', kwargs={'pk': self.outflow.pk}),
                {'product': self.product.pk, 'customer': self.customer.pk,
                 'quantity': '5', 'price': '15.00'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'já não existe')


class OutflowCreateProductDoesNotExistTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant)
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.cat = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_outflow_create_product_does_not_exist(self):
        with patch.object(QuerySet, 'select_for_update') as mock_sfu:
            mock_sfu.return_value.get.side_effect = Product.DoesNotExist
            response = self.client.post('/outflows/create/', {
                'product': self.product.pk, 'customer': self.customer.pk,
                'quantity': '5', 'price': '15.00',
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'já não existe')

    def test_outflow_create_quantity_exceeds_stock(self):
        response = self.client.post('/outflows/create/', {
            'product': self.product.pk, 'customer': self.customer.pk,
            'quantity': '999', 'price': '15.00',
        })
        self.assertEqual(response.status_code, 200)


class DeliveryEdgeCaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant)
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.cat = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.driver = Driver.objects.create(name='Drv', phone='123', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant,
        )
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=cls.tenant,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_delivery_create_exceeds_pending(self):
        Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('7'),
            driver=self.driver, tenant=self.tenant,
        )
        response = self.client.post(
            reverse('outflows:delivery_create', kwargs={'pk': self.outflow.pk}),
            {'quantity': '5', 'driver': self.driver.pk, 'delivered_at': '2026-05-26'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'excede o pendente')

    def test_delivery_create_exceeds_stock(self):
        Product.objects.filter(pk=self.product.pk).update(quantity=Decimal('3'))
        response = self.client.post(
            reverse('outflows:delivery_create', kwargs={'pk': self.outflow.pk}),
            {'quantity': '5', 'driver': self.driver.pk, 'delivered_at': '2026-05-26'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'excede o estoque dispon')

    def test_delivery_create_registry_does_not_exist(self):
        with patch.object(QuerySet, 'select_for_update') as mock_sfu:
            mock_qs = MagicMock()
            mock_sfu.return_value = mock_qs
            mock_qs.select_related.return_value.get.side_effect = Outflow.DoesNotExist
            response = self.client.post(
                reverse('outflows:delivery_create', kwargs={'pk': self.outflow.pk}),
                {'quantity': '3', 'driver': self.driver.pk, 'delivered_at': '2026-05-26'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'já não existe')

    def test_delivery_confirm_weight_double_confirm(self):
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=self.driver, is_confirmed=True,
            actual_quantity=Decimal('5'), tenant=self.tenant,
        )
        response = self.client.post(
            reverse('outflows:delivery_confirm_weight', kwargs={'pk': delivery.pk}),
            {'actual_quantity': '6'},
        )
        self.assertEqual(response.status_code, 200)

    def test_delivery_restore_not_deleted(self):
        delivery = Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('3'),
            driver=self.driver, tenant=self.tenant,
        )
        response = self.client.post(
            reverse('outflows:delivery_restore', kwargs={'pk': delivery.pk}),
        )
        self.assertRedirects(response, reverse('outflows:delivery_trash'))
