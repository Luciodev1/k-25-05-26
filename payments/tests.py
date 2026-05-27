"""Tests for payment views: CRUD and soft delete."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from customers.models import Customer
from suppliers.models import Supplier
from payments.models import Payment


class PaymentViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.customer = Customer.objects.create(name='Customer')
        cls.supplier = Supplier.objects.create(name='Supplier')
        cls.payment = Payment.objects.create(
            type='RECEIPT', customer=cls.customer,
            amount=Decimal('500.00'), payment_method='CASH',
            date=date.today(),
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
            date=date.today(),
        )
        payment.delete()
        response = self.client.post(f'/pagamentos/{payment.pk}/eliminar-permanente/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.all_objects.filter(pk=payment.pk).exists())
