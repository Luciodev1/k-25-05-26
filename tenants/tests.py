from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.urls import reverse
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


class TenantMiddlewareTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant1 = Tenant.objects.create(name='T1', slug='t1')
        cls.tenant2 = Tenant.objects.create(name='T2', slug='t2')

    def test_stale_session_clears_tenant(self):
        user = User.objects.create_user('regular', 'r@t.com', 'pass')
        TenantUser.objects.create(user=user, tenant=self.tenant1)
        self.client.force_login(user)
        session = self.client.session
        session['tenant_id'] = str(self.tenant1.pk)
        session.save()
        TenantUser.objects.all().delete()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('tenant_id', self.client.session)

    def test_multi_tenant_redirects_to_select(self):
        user = User.objects.create_superuser('multi', 'm@t.com', 'pass')
        TenantUser.objects.create(user=user, tenant=self.tenant1)
        TenantUser.objects.create(user=user, tenant=self.tenant2)
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, reverse('tenants:tenant_select'))


class TenantSelectViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant1 = Tenant.objects.create(name='Alpha', slug='alpha')
        cls.tenant2 = Tenant.objects.create(name='Beta', slug='beta')
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant1)
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant2)

    def test_tenant_select_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('tenants:tenant_select'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')
        self.assertContains(response, 'Beta')
        self.assertEqual(len(response.context['tenants_users']), 2)

    def test_tenant_select_post_valid(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('tenants:tenant_select'), {'tenant_id': self.tenant1.pk},
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.client.session['tenant_id'], str(self.tenant1.pk))

    def test_tenant_select_post_invalid(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('tenants:tenant_select'),
            {'tenant_id': '00000000-0000-0000-0000-000000000000'},
        )
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('inválida' in str(m) for m in messages))


class TenantCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')

    def test_tenant_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('tenants:tenant_create'))
        self.assertEqual(response.status_code, 200)

    def test_tenant_create_post_creates_settings_and_admin(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': 'NewCo', 'slug': 'newco',
            'currency': 'AOA', 'timezone': 'Africa/Luanda',
            'language': 'pt-pt', 'max_users': 10,
        })
        self.assertRedirects(response, reverse('tenants:tenant_list'))
        tenant = Tenant.objects.get(slug='newco')
        self.assertTrue(TenantSettings.objects.filter(tenant=tenant).exists())
        tu = TenantUser.objects.get(tenant=tenant, user=self.user)
        self.assertEqual(tu.role, 'admin')
        self.assertTrue(tu.is_primary)


class TenantDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='DetCo', slug='detco')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.u1 = User.objects.create_user('u1', 'u1@t.com', 'pass')
        cls.u2 = User.objects.create_user('u2', 'u2@t.com', 'pass')
        TenantUser.objects.create(user=cls.u1, tenant=cls.tenant, role='admin', is_primary=True)
        TenantUser.objects.create(user=cls.u2, tenant=cls.tenant, role='operator')

    def test_tenant_detail_context_has_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'u1')
        self.assertContains(response, 'u2')
        self.assertEqual(len(response.context['tenant_users']), 2)


class TenantUserAddViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='AddCo', slug='addco')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant, role='admin')
        cls.new_user = User.objects.create_user('newguy', 'n@t.com', 'pass')

    def test_tenant_user_add_get(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('tenants:tenant_user_add', kwargs={'pk': self.tenant.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIn(self.new_user, form.fields['user'].queryset)

    def test_tenant_user_add_post_valid(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('tenants:tenant_user_add', kwargs={'pk': self.tenant.pk}),
            {'user': self.new_user.pk, 'role': 'operator'},
        )
        self.assertRedirects(
            response,
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk}),
        )
        self.assertTrue(
            TenantUser.objects.filter(tenant=self.tenant, user=self.new_user).exists(),
        )

    def test_tenant_user_add_post_invalid(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('tenants:tenant_user_add', kwargs={'pk': self.tenant.pk}),
            {'user': '', 'role': 'operator'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_tenant_user_add_existing_user_excluded_from_queryset(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('tenants:tenant_user_add', kwargs={'pk': self.tenant.pk}),
        )
        form = response.context['form']
        self.assertNotIn(self.admin, form.fields['user'].queryset)


class TenantUserRemoveViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='RemCo', slug='remco')
        cls.admin = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        cls.primary_tu = TenantUser.objects.create(
            user=cls.admin, tenant=cls.tenant, role='admin', is_primary=True,
        )
        cls.other_user = User.objects.create_user('other', 'o@t.com', 'pass')
        cls.other_tu = TenantUser.objects.create(
            user=cls.other_user, tenant=cls.tenant, role='operator',
        )

    def test_remove_non_primary_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('tenants:tenant_user_remove', kwargs={
                'pk': self.tenant.pk, 'user_pk': self.other_user.pk,
            }),
        )
        self.assertRedirects(
            response,
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk}),
        )
        self.assertFalse(TenantUser.objects.filter(pk=self.other_tu.pk).exists())

    def test_cannot_remove_primary_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('tenants:tenant_user_remove', kwargs={
                'pk': self.tenant.pk, 'user_pk': self.admin.pk,
            }),
        )
        self.assertRedirects(
            response,
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk}),
        )
        self.assertTrue(TenantUser.objects.filter(pk=self.primary_tu.pk).exists())
