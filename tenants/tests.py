from django.test import TestCase
from django.contrib.auth.models import User
from .models import Tenant, TenantUser, TenantSettings


class TenantModelTest(TestCase):
    def test_create_tenant(self):
        tenant = Tenant.objects.create(name='TestEmpresa', slug='test-empresa')
        self.assertEqual(str(tenant), 'TestEmpresa')
        self.assertTrue(tenant.is_active)
        self.assertEqual(tenant.currency, 'AOA')

    def test_tenant_str(self):
        tenant = Tenant.objects.create(name='K Gestão', slug='k-gestao')
        self.assertEqual(str(tenant), 'K Gestão')

    def test_tenant_created_at_defaults(self):
        tenant = Tenant.objects.create(name='Test', slug='test')
        self.assertIsNotNone(tenant.created_at)
        self.assertIsNotNone(tenant.updated_at)


class TenantUserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('testuser', 't@t.com', 'pass')
        cls.tenant = Tenant.objects.create(name='Tenant', slug='tenant')

    def test_create_tenant_user(self):
        tu = TenantUser.objects.create(user=self.user, tenant=self.tenant, role='admin')
        self.assertEqual(str(tu), 'testuser - Tenant (admin)')
        self.assertTrue(tu.is_primary is False)

    def test_has_permission_admin(self):
        tu = TenantUser.objects.create(user=self.user, tenant=self.tenant, role='admin')
        self.assertTrue(tu.has_permission('view'))
        self.assertTrue(tu.has_permission('add'))
        self.assertTrue(tu.has_permission('manage'))

    def test_has_permission_viewer(self):
        tu = TenantUser.objects.create(user=self.user, tenant=self.tenant, role='viewer')
        self.assertTrue(tu.has_permission('view'))
        self.assertFalse(tu.has_permission('add'))
        self.assertFalse(tu.has_permission('delete'))

    def test_unique_together(self):
        TenantUser.objects.create(user=self.user, tenant=self.tenant)
        with self.assertRaises(Exception):
            TenantUser.objects.create(user=self.user, tenant=self.tenant)

    def test_get_tenant_users(self):
        TenantUser.objects.create(user=self.user, tenant=self.tenant)
        users = self.tenant.get_tenant_users()
        self.assertIn(self.user, users)

    def test_can_add_user(self):
        self.tenant.max_users = 0
        self.tenant.save()
        self.assertFalse(self.tenant.can_add_user())

    def test_get_active_users_count(self):
        TenantUser.objects.create(user=self.user, tenant=self.tenant)
        self.assertEqual(self.tenant.get_active_users_count(), 1)


class TenantSettingsModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Tenant', slug='tenant')

    def test_create_settings(self):
        ts = TenantSettings.objects.create(tenant=self.tenant)
        self.assertEqual(str(ts), 'Settings for Tenant')
        self.assertTrue(ts.email_notifications)
        self.assertEqual(ts.password_expiry_days, 90)
