from django.test import TestCase
from .models import Customer
from .forms import CustomerForm


class CustomerModelTest(TestCase):
    def test_create_customer(self):
        customer = Customer.objects.create(name='TestCustomer', phone='+244912345678', nif='123456789')
        self.assertEqual(str(customer), 'TestCustomer')

    def test_customer_ordering(self):
        Customer.objects.create(name='Zebra')
        Customer.objects.create(name='Alpha')
        customers = list(Customer.objects.values_list('name', flat=True))
        self.assertEqual(customers, ['Alpha', 'Zebra'])


class CustomerFormTest(TestCase):
    def test_valid_phone(self):
        form = CustomerForm(data={'name': 'Test', 'phone': '+244912345678', 'nif': '', 'address': '', 'email': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_phone(self):
        form = CustomerForm(data={'name': 'Test', 'phone': 'abc', 'nif': '', 'address': '', 'email': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_valid_nif(self):
        form = CustomerForm(data={'name': 'Test', 'phone': '', 'nif': '123456789', 'address': '', 'email': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_nif_too_short(self):
        form = CustomerForm(data={'name': 'Test', 'phone': '', 'nif': '12345', 'address': '', 'email': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('nif', form.errors)

    def test_valid_email(self):
        form = CustomerForm(data={'name': 'Test', 'phone': '', 'nif': '', 'address': '', 'email': 'test@email.com'})
        self.assertTrue(form.is_valid(), form.errors)


class CustomerViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(name='TestCustomer')

    def test_list_requires_login(self):
        response = self.client.get('/customers/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get('/customers/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestCustomer')

    def test_create_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post('/customers/create/', {
            'name': 'NewCustomer', 'phone': '', 'nif': '', 'address': '', 'email': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(name='NewCustomer').exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')

