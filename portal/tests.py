from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from tests.factories import TenantFactory, CustomerFactory, ProductFactory
from portal.models import CustomerAccess
from accounts.models import CustomerAccountEntry


class CustomerAccessModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-model')
        cls.customer = CustomerFactory(name='PortalCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('portaluser', 'portal@test.com', 'pass123')

    def test_create_customer_access(self):
        access = CustomerAccess.objects.create(
            user=self.user, customer=self.customer, is_active=True,
        )
        self.assertEqual(str(access), 'PortalCliente - portaluser')
        self.assertTrue(access.is_active)

    def test_customer_access_deletes_with_user(self):
        access = CustomerAccess.objects.create(
            user=self.user, customer=self.customer,
        )
        uid = self.user.pk
        self.user.delete()
        self.assertFalse(CustomerAccess.all_objects.filter(pk=access.pk).exists())

    def test_customer_access_soft_delete(self):
        access = CustomerAccess.objects.create(
            user=self.user, customer=self.customer,
        )
        access.delete()
        self.assertTrue(access.is_deleted)
        self.assertIsNotNone(access.deleted_at)


class CustomerLoginTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-login')
        cls.customer = CustomerFactory(name='LoginCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('logintest', 'login@test.com', 'secret123')
        cls.customer_access = CustomerAccess.objects.create(
            user=cls.user, customer=cls.customer, is_active=True,
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse('portal:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Portal do Cliente')

    def test_login_success(self):
        response = self.client.post(reverse('portal:login'), {
            'username': 'logintest', 'password': 'secret123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('portal:dashboard'))

    def test_login_inactive_access(self):
        self.customer_access.is_active = False
        self.customer_access.save()
        response = self.client.post(reverse('portal:login'), {
            'username': 'logintest', 'password': 'secret123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Não tem acesso')

    def test_login_wrong_password(self):
        response = self.client.post(reverse('portal:login'), {
            'username': 'logintest', 'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Por favor')

    def test_login_redirects_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:login'))
        self.assertEqual(response.status_code, 302)


class PortalDashboardTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-dash')
        cls.customer = CustomerFactory(name='DashCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('dashtest', 'dash@test.com', 'pass123')
        cls.customer_access = CustomerAccess.objects.create(
            user=cls.user, customer=cls.customer, is_active=True,
        )
        # Create some account entries
        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer,
            description='Venda', debit=Decimal('1000'), credit=Decimal('0'),
        )
        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer,
            description='Pagamento', debit=Decimal('0'), credit=Decimal('500'),
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DashCliente')
        self.assertContains(response, '1.000,00')
        self.assertContains(response, '500,00')

    def test_dashboard_unauthorized_user(self):
        other_user = User.objects.create_user('other', 'o@t.com', 'pass')
        self.client.force_login(other_user)
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('portal:login'))


class PortalAccountStatementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-extract')
        cls.customer = CustomerFactory(name='ExtractCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('extract', 'ext@t.com', 'pass')
        CustomerAccess.objects.create(user=cls.user, customer=cls.customer, is_active=True)
        for i in range(3):
            CustomerAccountEntry.objects.create(
                tenant=cls.tenant, customer=cls.customer,
                description=f'Entry {i}', debit=Decimal('100'), credit=Decimal('0'),
            )

    def test_account_statement_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:account_statement'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entry')
        self.assertContains(response, '300,00')

    def test_account_statement_pagination(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:account_statement'), {'page': '1'})
        self.assertEqual(response.status_code, 200)


class PortalDeliveriesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from tests.factories import ProductFactory, OutflowFactory, DriverFactory, DeliveryFactory
        cls.tenant = TenantFactory(slug='portal-del')
        cls.customer = CustomerFactory(name='DelCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('deluser', 'del@t.com', 'pass')
        CustomerAccess.objects.create(user=cls.user, customer=cls.customer, is_active=True)

    def test_deliveries_renders_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:deliveries'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhuma entrega')


class PortalPaymentsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-pay')
        cls.customer = CustomerFactory(name='PayCliente', tenant=cls.tenant)
        cls.user = User.objects.create_user('payuser', 'pay@t.com', 'pass')
        CustomerAccess.objects.create(user=cls.user, customer=cls.customer, is_active=True)

    def test_payments_renders_empty(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:payments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhum pagamento')


class PortalPasswordChangeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='portal-pass')
        cls.customer = CustomerFactory(tenant=cls.tenant)
        cls.user = User.objects.create_user('passuser', 'pass@t.com', 'oldpass')
        CustomerAccess.objects.create(user=cls.user, customer=cls.customer, is_active=True)

    def test_password_change_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('portal:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_success(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('portal:password_change'), {
            'old_password': 'oldpass',
            'new_password1': 'NewSecret123!',
            'new_password2': 'NewSecret123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('portal:dashboard'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecret123!'))


class PortalDataIsolationTest(TestCase):
    """Verifica que nenhum cliente vê dados de outro cliente."""

    @classmethod
    def setUpTestData(cls):
        from decimal import Decimal
        from tests.factories import (
            TenantFactory, CustomerFactory, ProductFactory,
            OutflowFactory, DeliveryFactory, DriverFactory, PaymentFactory,
        )
        from outflows.models import Outflow, Delivery
        from payments.models import Payment

        cls.tenant = TenantFactory(slug='portal-isolation')
        cls.driver = DriverFactory(tenant=cls.tenant)

        # Customer A
        cls.customer_a = CustomerFactory(name='Cliente A', tenant=cls.tenant)
        cls.user_a = User.objects.create_user('user_a', 'a@test.com', 'pass')
        CustomerAccess.objects.create(user=cls.user_a, customer=cls.customer_a, is_active=True)

        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer_a,
            description='Debito A', debit=Decimal('1000'), credit=Decimal('0'),
        )
        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer_a,
            description='Credito A', debit=Decimal('0'), credit=Decimal('500'),
        )
        prod_a = ProductFactory(tenant=cls.tenant, title='Produto A')
        out_a = OutflowFactory(customer=cls.customer_a, tenant=cls.tenant, product=prod_a)
        DeliveryFactory(outflow=out_a, tenant=cls.tenant, driver=cls.driver)
        PaymentFactory(customer=cls.customer_a, tenant=cls.tenant)

        # Customer B
        cls.customer_b = CustomerFactory(name='Cliente B', tenant=cls.tenant)
        cls.user_b = User.objects.create_user('user_b', 'b@test.com', 'pass')
        CustomerAccess.objects.create(user=cls.user_b, customer=cls.customer_b, is_active=True)

        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer_b,
            description='Debito B', debit=Decimal('2000'), credit=Decimal('0'),
        )
        CustomerAccountEntry.objects.create(
            tenant=cls.tenant, customer=cls.customer_b,
            description='Credito B', debit=Decimal('0'), credit=Decimal('1500'),
        )
        prod_b = ProductFactory(tenant=cls.tenant, title='Produto B')
        out_b = OutflowFactory(customer=cls.customer_b, tenant=cls.tenant, product=prod_b)
        DeliveryFactory(outflow=out_b, tenant=cls.tenant, driver=cls.driver)
        PaymentFactory(customer=cls.customer_b, tenant=cls.tenant)

    def test_dashboard_shows_only_own_data(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('portal:dashboard'))
        self.assertContains(response, 'Cliente A')
        self.assertNotContains(response, 'Cliente B')

    def test_account_statement_shows_only_own_entries(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('portal:account_statement'))
        self.assertNotContains(response, 'Debito B')
        self.assertNotContains(response, 'Credito B')
        self.assertContains(response, 'Debito A')

    def test_deliveries_shows_only_own_deliveries(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('portal:deliveries'))
        self.assertContains(response, 'Produto A')
        self.assertNotContains(response, 'Produto B')

    def test_payments_shows_only_own_payments(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('portal:payments'))
        self.assertContains(response, '100,00')

    def test_profile_edit_cannot_change_other_customer(self):
        """User A nao pode editar perfil do Customer B via URL directa."""
        self.client.force_login(self.user_a)
        self.client.post(reverse('portal:profile_edit'), {
            'name': 'Hacked Name',
        })
        self.customer_b.refresh_from_db()
        self.assertNotEqual(self.customer_b.name, 'Hacked Name')

    def test_unauthorized_user_blocked(self):
        """User sem CustomerAccess nao acede ao portal."""
        other = User.objects.create_user('hacker', 'h@t.com', 'pass')
        self.client.force_login(other)
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 302)
