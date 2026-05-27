"""Tests for account views: payments, balances, account statements."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from suppliers.models import Supplier
from outflows.models import Outflow
from inflows.models import Inflow
from accounts.models import CustomerAccountEntry, SupplierAccountEntry


class AccountViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.brand = Brand.objects.create(name='Brand')
        cls.category = Category.objects.create(name='Cat')
        cls.customer = Customer.objects.create(name='Test Customer')
        cls.supplier = Supplier.objects.create(name='Test Supplier')
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'),
            quantity=Decimal('100'),
        )
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        cls.inflow = Inflow.objects.create(
            product=cls.product, supplier=cls.supplier,
            quantity=Decimal('20'), price=Decimal('10.00'),
        )

    def test_customer_account_view(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/customer/{self.customer.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')
        self.assertIn('balance', response.context)

    def test_customer_account_requires_permission(self):
        basic = User.objects.create_user('basic', password='pass')
        self.client.force_login(basic)
        response = self.client.get(f'/accounts/customer/{self.customer.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_supplier_account_view(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/supplier/{self.supplier.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Supplier')
        self.assertIn('balance', response.context)

    def test_supplier_account_requires_permission(self):
        basic = User.objects.create_user('basic2', password='pass')
        self.client.force_login(basic)
        response = self.client.get(f'/accounts/supplier/{self.supplier.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_customer_payment_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/customer/{self.customer.pk}/payment/')
        self.assertEqual(response.status_code, 200)

    def test_customer_payment_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/accounts/customer/{self.customer.pk}/payment/',
            {
                'customer': self.customer.pk,
                'amount': '100.00',
                'payment_method': 'CASH',
                'date': '2026-05-26',
                'description': 'Test payment'
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CustomerAccountEntry.objects.filter(credit=Decimal('100.00')).exists()
        )

    def test_supplier_payment_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/supplier/{self.supplier.pk}/payment/')
        self.assertEqual(response.status_code, 200)

    def test_supplier_payment_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/accounts/supplier/{self.supplier.pk}/payment/',
            {
                'supplier': self.supplier.pk,
                'amount': '200.00',
                'payment_method': 'TRANSFER',
                'date': '2026-05-26',
                'description': 'Test payment'
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SupplierAccountEntry.objects.filter(debit=Decimal('200.00')).exists()
        )

    def test_customer_balances_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/accounts/customer-balances/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')

    def test_supplier_balances_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/accounts/supplier-balances/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Supplier')


class AccountEntryUpdateDeleteTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.brand = Brand.objects.create(name='B')
        cls.category = Category.objects.create(name='C')
        cls.customer = Customer.objects.create(name='Cust')
        cls.supplier = Supplier.objects.create(name='Supp')
        cls.product = Product.objects.create(
            title='P', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('100'),
        )
        cls.customer_entry = CustomerAccountEntry.objects.create(
            customer=cls.customer, debit=Decimal('100'), credit=Decimal('0'),
            description='Test debit', date='2026-01-01',
        )
        cls.supplier_entry = SupplierAccountEntry.objects.create(
            supplier=cls.supplier, debit=Decimal('0'), credit=Decimal('200'),
            description='Test credit', date='2026-01-01',
        )

    def test_customer_entry_update_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/customer-entry/{self.customer_entry.pk}/update/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test debit')

    def test_customer_entry_update_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/accounts/customer-entry/{self.customer_entry.pk}/update/',
            {'description': 'Updated', 'debit': '150', 'credit': '0'},
        )
        self.assertEqual(response.status_code, 302)
        self.customer_entry.refresh_from_db()
        self.assertEqual(self.customer_entry.description, 'Updated')
        self.assertEqual(self.customer_entry.debit, Decimal('150'))

    def test_customer_entry_delete_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/customer-entry/{self.customer_entry.pk}/delete/')
        self.assertEqual(response.status_code, 200)

    def test_customer_entry_delete_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/accounts/customer-entry/{self.customer_entry.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomerAccountEntry.objects.filter(pk=self.customer_entry.pk).exists())

    def test_supplier_entry_update_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/accounts/supplier-entry/{self.supplier_entry.pk}/update/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test credit')

    def test_supplier_entry_update_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/accounts/supplier-entry/{self.supplier_entry.pk}/update/',
            {'description': 'Updated supp', 'debit': '0', 'credit': '250'},
        )
        self.assertEqual(response.status_code, 302)
        self.supplier_entry.refresh_from_db()
        self.assertEqual(self.supplier_entry.description, 'Updated supp')
        self.assertEqual(self.supplier_entry.credit, Decimal('250'))

    def test_supplier_entry_delete_view_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/accounts/supplier-entry/{self.supplier_entry.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SupplierAccountEntry.objects.filter(pk=self.supplier_entry.pk).exists())


class AccountEntryModelTest(TestCase):
    """Test CheckConstraints on account entries."""

    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='B')
        cls.category = Category.objects.create(name='C')
        cls.customer = Customer.objects.create(name='Cust')
        cls.supplier = Supplier.objects.create(name='Supp')
        cls.product = Product.objects.create(
            title='P', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('100'),
        )

    def test_customer_entry_str(self):
        entry = CustomerAccountEntry.objects.create(
            customer=self.customer, debit=Decimal('100'), credit=Decimal('0'),
            date='2026-01-01',
        )
        self.assertIn('Cust', str(entry))

    def test_supplier_entry_str(self):
        entry = SupplierAccountEntry.objects.create(
            supplier=self.supplier, debit=Decimal('0'), credit=Decimal('100'),
            date='2026-01-01',
        )
        self.assertIn('Supp', str(entry))


class PaymentFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(name='FCust')
        cls.supplier = Supplier.objects.create(name='FSupp')

    def test_customer_payment_form_valid(self):
        from accounts.forms import CustomerPaymentForm
        form = CustomerPaymentForm(
            data={'customer': self.customer.pk, 'amount': '50.00', 'payment_method': 'CASH', 'date': '2026-05-27'},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_customer_payment_form_invalid_amount_zero(self):
        from accounts.forms import CustomerPaymentForm
        form = CustomerPaymentForm(
            data={'customer': self.customer.pk, 'amount': '0.00', 'payment_method': 'CASH', 'date': '2026-05-27'},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_supplier_payment_form_valid(self):
        from accounts.forms import SupplierPaymentForm
        form = SupplierPaymentForm(
            data={'supplier': self.supplier.pk, 'amount': '75.00', 'payment_method': 'TRANSFER', 'date': '2026-05-27'},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_supplier_payment_form_invalid_amount_zero(self):
        from accounts.forms import SupplierPaymentForm
        form = SupplierPaymentForm(
            data={'supplier': self.supplier.pk, 'amount': '0.00', 'payment_method': 'TRANSFER', 'date': '2026-05-27'},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
