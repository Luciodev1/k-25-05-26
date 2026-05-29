"""Tests for inflow views and signals."""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from products.models import Product
from inflows.models import Inflow
from tenants.models import TenantUser
from tests.factories import TenantFactory, BrandFactory, CategoryFactory, SupplierFactory, ProductFactory, InflowFactory


class InflowSignalTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='x-test')
        cls.brand = BrandFactory(name='Brand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='Cat', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='Supplier', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Product', category=cls.category, brand=cls.brand,
            tenant=cls.tenant,
        )

    def test_inflow_increases_stock(self):
        self.assertEqual(self.product.quantity, Decimal('100'))
        InflowFactory(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('50'), price=Decimal('10.00'),
            tenant=self.tenant,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('150'))

    def test_inflow_delete_decreases_stock(self):
        inflow = InflowFactory(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('30'), price=Decimal('10.00'),
            tenant=self.tenant,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('130'))
        inflow.delete()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('100'))

    def test_multiple_inflows_accumulate(self):
        InflowFactory(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('10'), price=Decimal('10.00'),
            tenant=self.tenant,
        )
        InflowFactory(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10.00'),
            tenant=self.tenant,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal('130'))


class InflowViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='x-test2')
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')
        cls.brand = BrandFactory(name='Brand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='Cat', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='Supplier', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Product', category=cls.category, brand=cls.brand,
            tenant=cls.tenant,
        )
        cls.inflow = InflowFactory(
            product=cls.product, supplier=cls.supplier,
            quantity=Decimal('20'), price=Decimal('10.00'),
            tenant=cls.tenant,
        )

    def test_inflow_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inflows:inflow_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product')

    def test_inflow_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inflows:inflow_detail', kwargs={'pk': self.inflow.pk}))
        self.assertEqual(response.status_code, 200)

    def test_inflow_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inflows:inflow_create'))
        self.assertEqual(response.status_code, 200)

    def test_inflow_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('inflows:inflow_create'), {
            'product': self.product.pk,
            'supplier': self.supplier.pk,
            'quantity': '30',
            'price': '12.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Inflow.objects.filter(quantity=Decimal('30')).exists())

    def test_inflow_update_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inflows:inflow_update', kwargs={'pk': self.inflow.pk}))
        self.assertEqual(response.status_code, 200)

    def test_inflow_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('inflows:inflow_update', kwargs={'pk': self.inflow.pk}), {
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
        response = self.client.get(reverse('inflows:inflow_delete', kwargs={'pk': self.inflow.pk}))
        self.assertEqual(response.status_code, 200)

    def test_inflow_soft_delete(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('inflows:inflow_delete', kwargs={'pk': self.inflow.pk}))
        self.assertEqual(response.status_code, 302)
        self.inflow.refresh_from_db()
        self.assertTrue(self.inflow.is_deleted)

    def test_inflow_trash_list(self):
        self.client.force_login(self.user)
        self.inflow.delete()
        response = self.client.get(reverse('inflows:inflow_trash'))
        self.assertEqual(response.status_code, 200)

    def test_inflow_restore(self):
        self.client.force_login(self.user)
        self.inflow.delete()
        response = self.client.post(reverse('inflows:inflow_restore', kwargs={'pk': self.inflow.pk}))
        self.assertEqual(response.status_code, 302)
        self.inflow.refresh_from_db()
        self.assertFalse(self.inflow.is_deleted)

    def test_inflow_hard_delete(self):
        self.client.force_login(self.user)
        inflow = InflowFactory(
            product=self.product, supplier=self.supplier,
            quantity=Decimal('5'), price=Decimal('10.00'),
            tenant=self.tenant,
        )
        inflow.delete()
        response = self.client.post(reverse('inflows:inflow_hard_delete', kwargs={'pk': inflow.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Inflow.all_objects.filter(pk=inflow.pk).exists())


class InflowFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='x-test3')
        cls.brand = BrandFactory(name='B', tenant=cls.tenant)
        cls.cat = CategoryFactory(name='C', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='S', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='P', category=cls.cat, brand=cls.brand,
            quantity=Decimal('0'), tenant=cls.tenant,
        )

    def test_inflow_form_valid(self):
        from inflows.forms import InflowForm
        form = InflowForm(data={
            'product': self.product.pk, 'supplier': self.supplier.pk,
            'quantity': '10', 'price': '12.00',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_inflow_form_quantity_zero_or_negative(self):
        from inflows.forms import InflowForm
        for qty in ['0', '-1']:
            form = InflowForm(data={
                'product': self.product.pk, 'supplier': self.supplier.pk,
                'quantity': qty, 'price': '12.00',
            })
            self.assertFalse(form.is_valid())

    def test_inflow_form_tenant_filtering(self):
        from inflows.forms import InflowForm
        tenant = TenantFactory(slug='t')
        tenant_product = ProductFactory(
            title='TP', category=self.cat, brand=self.brand,
            quantity=Decimal('5'), tenant=tenant,
        )
        tenant_supplier = SupplierFactory(name='TS', tenant=tenant)
        other = ProductFactory(
            title='Other', category=self.cat, brand=self.brand,
            quantity=Decimal('5'),
        )
        form = InflowForm(tenant=tenant)
        self.assertIn(tenant_product, form.fields['product'].queryset)
        self.assertIn(tenant_supplier, form.fields['supplier'].queryset)
        self.assertNotIn(other, form.fields['product'].queryset)
        self.assertNotIn(self.supplier, form.fields['supplier'].queryset)
