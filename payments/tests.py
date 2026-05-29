"""Tests for payment views: CRUD and soft delete."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from payments.models import Payment
from tenants.models import TenantUser
from tests.factories import TenantFactory, CustomerFactory, SupplierFactory, PaymentFactory


class PaymentViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.tenant = TenantFactory(slug='pay-vt')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')
        cls.customer = CustomerFactory(name='Customer', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='Supplier', tenant=cls.tenant)
        cls.payment = PaymentFactory(
            customer=cls.customer,
            amount=Decimal('500.00'),
            date=date.today(), tenant=cls.tenant,
        )

    def test_payment_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payments:payment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '500,00')

    def test_payment_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payments:payment_detail', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_payment_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('payments:payment_create'))
        self.assertEqual(response.status_code, 200)

    def test_payment_create_post_receipt(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('payments:payment_create'), {
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
        response = self.client.post(reverse('payments:payment_create'), {
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
        response = self.client.get(reverse('payments:payment_update', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_payment_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('payments:payment_update', kwargs={'pk': self.payment.pk}), {
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
        response = self.client.get(reverse('payments:payment_delete', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_payment_soft_delete_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('payments:payment_delete', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.is_deleted)

    def test_payment_trash_list(self):
        self.client.force_login(self.user)
        self.payment.delete()
        response = self.client.get(reverse('payments:payment_trash'))
        self.assertEqual(response.status_code, 200)

    def test_payment_restore(self):
        self.client.force_login(self.user)
        self.payment.delete()
        response = self.client.post(reverse('payments:payment_restore', kwargs={'pk': self.payment.pk}))
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.is_deleted)

    def test_payment_hard_delete(self):
        self.client.force_login(self.user)
        payment = PaymentFactory(
            customer=self.customer,
            amount=Decimal('50.00'),
            date=date.today(), tenant=self.tenant,
        )
        payment.delete()
        response = self.client.post(reverse('payments:payment_hard_delete', kwargs={'pk': payment.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.all_objects.filter(pk=payment.pk).exists())


class PaymentFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='pay-ft')
        cls.customer = CustomerFactory(name='C', tenant=cls.tenant)
        cls.supplier = SupplierFactory(name='S', tenant=cls.tenant)

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
        tenant = TenantFactory(slug='t')
        tenant_cust = CustomerFactory(name='TC', tenant=tenant)
        tenant_supp = SupplierFactory(name='TS', tenant=tenant)
        other_cust = CustomerFactory(name='Other')
        other_supp = SupplierFactory(name='Other')
        form = PaymentForm(tenant=tenant)
        self.assertIn(tenant_cust, form.fields['customer'].queryset)
        self.assertIn(tenant_supp, form.fields['supplier'].queryset)
        self.assertNotIn(other_cust, form.fields['customer'].queryset)
        self.assertNotIn(other_supp, form.fields['supplier'].queryset)
