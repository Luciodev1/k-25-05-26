from django import forms
from django.test import TestCase
from django.urls import reverse
from .models import Supplier
from tenants.models import TenantUser
from tests.factories import TenantFactory, SupplierFactory


class SupplierModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='test-supplier-model')

    def test_create_supplier(self):
        supplier = SupplierFactory(name='TestSupplier', description='Desc', tenant=self.tenant)
        self.assertEqual(str(supplier), 'TestSupplier')

    def test_supplier_ordering(self):
        SupplierFactory(name='Zebra', tenant=self.tenant)
        SupplierFactory(name='Alpha', tenant=self.tenant)
        suppliers = list(Supplier.objects.values_list('name', flat=True))
        self.assertEqual(suppliers, ['Alpha', 'Zebra'])


class SupplierViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User
        cls.tenant = TenantFactory(slug='test-supplier-view')
        cls.supplier = SupplierFactory(name='TestSupplier', tenant=cls.tenant)
        cls.user = User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant)

    def test_list_requires_login(self):
        response = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_create_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('suppliers:supplier_create'), {'name': 'NewSupplier', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name='NewSupplier').exists())

    def test_update_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('suppliers:supplier_update', kwargs={'pk': self.supplier.pk}), {
            'name': 'Updated', 'description': '',
        })
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, 'Updated')

    def test_detail_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('suppliers:supplier_detail', kwargs={'pk': self.supplier.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_delete_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('suppliers:supplier_delete', kwargs={'pk': self.supplier.pk}))
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_deleted)

    def test_trash_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.get(reverse('suppliers:supplier_trash'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_restore_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.post(reverse('suppliers:supplier_restore', kwargs={'pk': self.supplier.pk}))
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_deleted)

    def test_hard_delete_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.post(reverse('suppliers:supplier_hard_delete', kwargs={'pk': self.supplier.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Supplier.all_objects.filter(pk=self.supplier.pk).exists())


class SupplierExportTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User
        cls.tenant = TenantFactory(slug='test-supplier-export')
        cls.supplier = SupplierFactory(name='ExportTest', tenant=cls.tenant)
        cls.user = User.objects.create_superuser('exportuser', 'e@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant)

    def test_export_excel_content_type(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('suppliers:supplier_list') + '?export=excel')
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class SupplierFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='test-supplier-form')

    def test_supplier_form_valid(self):
        from suppliers.forms import SupplierForm
        form = SupplierForm(data={'name': 'Test', 'nif': '123456789'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_supplier_form_invalid_nif(self):
        from suppliers.forms import SupplierForm
        form = SupplierForm(data={'name': 'Test', 'nif': '12345'})
        self.assertFalse(form.is_valid())
        self.assertIn('nif', form.errors)

    def test_supplier_form_invalid_empty_name(self):
        from suppliers.forms import SupplierForm
        form = SupplierForm(data={'name': '', 'nif': ''})
        self.assertFalse(form.is_valid())

    def test_supplier_form_save_integrity_error(self):
        from suppliers.forms import SupplierForm
        tenant = TenantFactory(slug='t')
        form = SupplierForm(data={'name': 'S1', 'nif': '123456789'})
        self.assertTrue(form.is_valid())
        form.instance.tenant = tenant
        form.save()
        form2 = SupplierForm(data={'name': 'S2', 'nif': '123456789'})
        self.assertTrue(form2.is_valid())
        form2.instance.tenant = tenant
        with self.assertRaises(forms.ValidationError):
            form2.save()

    def test_supplier_delete_logs_action(self):
        from unittest.mock import patch
        supplier = SupplierFactory(name='LogTest', nif='987654321', tenant=self.tenant)
        with patch('suppliers.models.log_action') as mock_log:
            supplier.delete()
            mock_log.assert_called_once_with(supplier, 'DELETE')
