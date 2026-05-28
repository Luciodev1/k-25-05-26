from django import forms
from django.test import TestCase
from .models import Supplier
from tenants.models import Tenant, TenantUser


class SupplierModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='TestSupplierModel', slug='test-supplier-model')

    def test_create_supplier(self):
        supplier = Supplier.objects.create(name='TestSupplier', description='Desc', tenant=self.tenant)
        self.assertEqual(str(supplier), 'TestSupplier')

    def test_supplier_ordering(self):
        Supplier.objects.create(name='Zebra', tenant=self.tenant)
        Supplier.objects.create(name='Alpha', tenant=self.tenant)
        suppliers = list(Supplier.objects.values_list('name', flat=True))
        self.assertEqual(suppliers, ['Alpha', 'Zebra'])


class SupplierViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User
        cls.tenant = Tenant.objects.create(name='TestSupplierView', slug='test-supplier-view')
        cls.supplier = Supplier.objects.create(name='TestSupplier', tenant=cls.tenant)
        cls.user = User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant)

    def test_list_requires_login(self):
        response = self.client.get('/suppliers/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/suppliers/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_create_view(self):
        self.client.force_login(self.user)
        response = self.client.post('/suppliers/create/', {'name': 'NewSupplier', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name='NewSupplier').exists())

    def test_update_view(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/suppliers/{self.supplier.pk}/update/', {
            'name': 'Updated', 'description': '',
        })
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, 'Updated')

    def test_detail_view(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/suppliers/{self.supplier.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_delete_view(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/suppliers/{self.supplier.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_deleted)

    def test_trash_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.get('/suppliers/trash/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_restore_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.post(f'/suppliers/{self.supplier.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_deleted)

    def test_hard_delete_view(self):
        self.client.force_login(self.user)
        self.supplier.delete()
        response = self.client.post(f'/suppliers/{self.supplier.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Supplier.all_objects.filter(pk=self.supplier.pk).exists())


class SupplierFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='TestSupplierForm', slug='test-supplier-form')

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
        tenant = Tenant.objects.create(name='T', slug='t')
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
        supplier = Supplier.objects.create(name='LogTest', nif='987654321', tenant=self.tenant)
        with patch('suppliers.models.log_action') as mock_log:
            supplier.delete()
            mock_log.assert_called_once_with(supplier, 'DELETE')
