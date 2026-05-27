from django.test import TestCase
from .models import Supplier


class SupplierModelTest(TestCase):
    def test_create_supplier(self):
        supplier = Supplier.objects.create(name='TestSupplier', description='Desc')
        self.assertEqual(str(supplier), 'TestSupplier')

    def test_supplier_ordering(self):
        Supplier.objects.create(name='Zebra')
        Supplier.objects.create(name='Alpha')
        suppliers = list(Supplier.objects.values_list('name', flat=True))
        self.assertEqual(suppliers, ['Alpha', 'Zebra'])


class SupplierViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.supplier = Supplier.objects.create(name='TestSupplier')

    def test_list_requires_login(self):
        response = self.client.get('/suppliers/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get('/suppliers/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestSupplier')

    def test_create_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post('/suppliers/create/', {'name': 'NewSupplier', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name='NewSupplier').exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')



class SupplierFormTest(TestCase):
    def test_supplier_form_valid(self):
        from suppliers.forms import SupplierForm
        form = SupplierForm(data={'name': 'Test', 'nif': '123456789'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_supplier_form_invalid_nif(self):
        from suppliers.forms import SupplierForm
        form = SupplierForm(data={'name': 'Test', 'nif': '12345'})
        self.assertFalse(form.is_valid())
        self.assertIn('nif', form.errors)
