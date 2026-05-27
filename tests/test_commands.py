from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from tenants.models import Tenant, TenantUser


class CreateTenantCommandTest(TestCase):
    def test_create_tenant_success(self):
        out = StringIO()
        call_command('create_tenant', 'MinhaEmpresa', 'minha-empresa', stdout=out)
        self.assertTrue(Tenant.objects.filter(slug='minha-empresa').exists())
        self.assertIn('sucesso', out.getvalue().lower())

    def test_create_tenant_duplicate_slug(self):
        Tenant.objects.create(name='Existing', slug='existing')
        out = StringIO()
        call_command('create_tenant', 'Duplicate', 'existing', stderr=out)
        self.assertIn('existe', out.getvalue().lower())

    def test_create_tenant_with_user(self):
        user = User.objects.create_user('adminuser', 'admin@test.com', 'pass')
        out = StringIO()
        call_command('create_tenant', 'ComUser', 'com-user', f'--username={user.username}', stdout=out)
        tenant = Tenant.objects.get(slug='com-user')
        self.assertTrue(TenantUser.objects.filter(user=user, tenant=tenant, role='admin').exists())

    def test_create_tenant_with_nonexistent_user(self):
        out = StringIO()
        call_command('create_tenant', 'NoUser', 'no-user', '--username=nobody', stderr=out)
        self.assertIn('não encontrado', out.getvalue())
        self.assertTrue(Tenant.objects.filter(slug='no-user').exists())
