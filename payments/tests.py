"""Tests for payment views: CRUD and soft delete."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from customers.models import Customer
from suppliers.models import Supplier
from payments.models import Payment
from tenants.models import Tenant, TenantUser


class PaymentViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.tenant = Tenant.objects.create(name='PayVT', slug='pay-vt')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')
        cls.customer = Customer.objects.create(name='Customer', tenant=cls.tenant)
        cls.supplier = Supplier.objects.create(name='Supplier', tenant=cls.tenant)
        cls.payment = Payment.objects.create(
            type='RECEIPT', customer=cls.customer,
            amount=Decimal('500.00'), payment_method='CASH',
            date=date.today(), tenant=cls.tenant,
        )

    def test_payment_list(self):
        self.client.force_login(self.user)
        response = self.client.get('/pagamentos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '500,00')

    def test_payment_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/pagamentos/{self.payment.pk}/detalhe/')
        self.assertEqual(response.status_code, 200)

    def test_payment_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get('/pagamentos/novo/')
        self.assertEqual(response.status_code, 200)

    def test_payment_create_post_receipt(self):
        self.client.force_login(self.user)
        response = self.client.post('/pagamentos/novo/', {
            'type': 'RECEIPT',
            'customer': self.customer.pk,
            'amount': '300.00',
            'payment_method': 'CASH',
            'date': '2026-01-15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(amount=Decimal('300.00')).exists())

    def test_payment_create_post_payment_to_supplier(self):
        self.client.force_login(self.user)
        response = self.client.post('/pagamentos/novo/', {
            'type': 'PAYMENT',
            'supplier': self.supplier.pk,
            'amount': '200.00',
            'payment_method': 'TRANSFER',
            'date': '2026-01-15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(type='PAYMENT').exists())

    def test_payment_update_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/pagamentos/{self.payment.pk}/editar/')
        self.assertEqual(response.status_code, 200)

    def test_payment_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/pagamentos/{self.payment.pk}/editar/', {
            'type': 'RECEIPT',
            'customer': self.customer.pk,
            'amount': '750.00',
            'payment_method': 'CASH',
            'date': '2026-01-15',
        })
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.amount, Decimal('750.00'))

    def test_payment_delete_get(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/pagamentos/{self.payment.pk}/eliminar/')
        self.assertEqual(response.status_code, 200)

    def test_payment_soft_delete_post(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/pagamentos/{self.payment.pk}/eliminar/')
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_deleted)

    def test_payment_trash_list(self):
        self.client.force_login(self.user)
        self.payment.delete()
        response = self.client.get('/pagamentos/lixeira/')
        self.assertEqual(response.status_code, 200)

    def test_payment_restore(self):
        self.client.force_login(self.user)
        self.payment.delete()
        response = self.client.post(f'/pagamentos/{self.payment.pk}/restaurar/')
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.is_deleted)

    def test_payment_hard_delete(self):
        self.client.force_login(self.user)
        payment = Payment.objects.create(
            type='RECEIPT', customer=self.customer,
            amount=Decimal('50.00'), payment_method='CASH',
            date=date.today(), tenant=self.tenant,
        )
        payment.delete()
        response = self.client.post(f'/pagamentos/{payment.pk}/eliminar-permanente/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.all_objects.filter(pk=payment.pk).exists())


class PaymentFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='PayFT', slug='pay-ft')
        cls.customer = Customer.objects.create(name='C', tenant=cls.tenant)
        cls.supplier = Supplier.objects.create(name='S', tenant=cls.tenant)

    def test_payment_form_valid_receipt(self):
        from payments.forms import PaymentForm
        form = PaymentForm(data={
            'type': 'RECEIPT', 'customer': self.customer.pk,
            'amount': '100.00', 'payment_method': 'CASH',
            'date': '2026-05-27',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_payment_form_valid_payment(self):
        from payments.forms import PaymentForm
        form = PaymentForm(data={
            'type': 'PAYMENT', 'supplier': self.supplier.pk,
            'amount': '100.00', 'payment_method': 'CASH',
            'date': '2026-05-27',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_payment_form_receipt_requires_customer(self):
        from payments.forms import PaymentForm
        form = PaymentForm(data={
            'type': 'RECEIPT', 'supplier': self.supplier.pk,
            'amount': '100.00', 'payment_method': 'CASH',
            'date': '2026-05-27',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('customer', form.errors)

    def test_payment_form_payment_requires_supplier(self):
        from payments.forms import PaymentForm
        form = PaymentForm(data={
            'type': 'PAYMENT', 'customer': self.customer.pk,
            'amount': '100.00', 'payment_method': 'CASH',
            'date': '2026-05-27',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('supplier', form.errors)

    def test_payment_form_tenant_filtering(self):
        from payments.forms import PaymentForm
        tenant = Tenant.objects.create(name='T', slug='t')
        tenant_cust = Customer.objects.create(name='TC', tenant=tenant)
        tenant_supp = Supplier.objects.create(name='TS', tenant=tenant)
        other_cust = Customer.objects.create(name='Other')
        other_supp = Supplier.objects.create(name='Other')
        form = PaymentForm(tenant=tenant)
        self.assertIn(tenant_cust, form.fields['customer'].queryset)
        self.assertIn(tenant_supp, form.fields['supplier'].queryset)
        self.assertNotIn(other_cust, form.fields['customer'].queryset)
        self.assertNotIn(other_supp, form.fields['supplier'].queryset)
