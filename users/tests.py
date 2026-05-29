from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from tenants.models import TenantUser
from tests.factories import TenantFactory


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user('testuser', 'test@email.com', 'testpass123')
        self.assertEqual(str(user), 'testuser')
        self.assertTrue(user.check_password('testpass123'))

    def test_create_superuser(self):
        admin = User.objects.create_superuser('admin', 'admin@email.com', 'adminpass')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)

    def test_profile_str(self):
        from users.models import Profile
        user = User.objects.create_user('puser', 'p@test.com', 'pass')
        profile = Profile.objects.get(user=user)
        self.assertEqual(str(profile), f'Perfil de {user.username}')


class UserViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@email.com', 'adminpass')
        cls.user = User.objects.create_user('testuser', password='testpass123')

    def test_list_requires_login(self):
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_list_view_with_permission(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_create_user_view(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('users:user_create'), {
            'username': 'newuser',
            'email': 'new@email.com',
            'password': 'StrongPass123!',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())


class GroupViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@email.com', 'adminpass')
        cls.group = Group.objects.create(name='TestGroup')

    def test_list_requires_login(self):
        response = self.client.get(reverse('users:group_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('users:group_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestGroup')

    def test_create_group(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('users:group_create'), {'name': 'NewGroup', 'permissions': []})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Group.objects.filter(name='NewGroup').exists())


class UserProfileAndAccessSecurityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('adminuser', 'admin@example.com', 'adminpass')
        cls.basic_user = User.objects.create_user('regularuser', 'user@example.com', 'userpass')
        cls.manager_group = Group.objects.create(name='Gerente')
        cls.manager_user = User.objects.create_user('manageruser', 'manager@example.com', 'managerpass')
        cls.manager_user.groups.add(cls.manager_group)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('users:user_profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_view_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('users:user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meu Perfil')
        self.assertContains(response, 'Administrador')
        self.assertContains(response, 'adminuser')

    def test_profile_view_for_manager_group(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse('users:user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerente')
        self.assertContains(response, 'manageruser')

    def test_profile_view_for_operator_fallback(self):
        self.client.force_login(self.basic_user)
        response = self.client.get(reverse('users:user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operador')
        self.assertContains(response, 'regularuser')

    def test_reports_index_requires_permissions(self):
        # Sem nenhuma permissão relevante
        self.client.force_login(self.basic_user)
        response = self.client.get(reverse('reports:report_index'))
        self.assertEqual(response.status_code, 403)

        # Com permissão relacionada (mas sem tenant, continua bloqueado)
        view_outflow = Permission.objects.get(codename='view_outflow')
        self.basic_user.user_permissions.add(view_outflow)
        
        user_with_perm = User.objects.get(id=self.basic_user.id)
        self.client.force_login(user_with_perm)
        response = self.client.get(reverse('reports:report_index'))
        self.assertEqual(response.status_code, 403)

    def test_specific_reports_restricted(self):
        self.client.force_login(self.basic_user)
        
        response = self.client.get(reverse('reports:report_outflows_by_customer'))
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get(reverse('reports:report_deliveries'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse('reports:report_customer_account'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse('reports:report_supplier_account'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse('reports:report_balances'))
        self.assertEqual(response.status_code, 403)

    def test_specific_reports_accessible_with_perms(self):
        view_outflow = Permission.objects.get(codename='view_outflow')
        self.basic_user.user_permissions.add(view_outflow)
        user_with_perm = User.objects.get(id=self.basic_user.id)
        self.client.force_login(user_with_perm)

        # Utilizador sem tenant associado — acesso negado mesmo com permissão
        response = self.client.get(reverse('reports:report_outflows_by_customer'))
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get(reverse('reports:report_deliveries'))
        self.assertEqual(response.status_code, 403)

    def test_audit_logs_restricted_to_authorized_only(self):
        self.client.force_login(self.basic_user)
        
        response = self.client.get(reverse('audit:audit_list'))
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get(reverse('audit:activity_feed'))
        self.assertEqual(response.status_code, 403)

    def test_audit_logs_accessible_for_superuser(self):
        self.client.force_login(self.superuser)
        
        response = self.client.get(reverse('audit:audit_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('audit:activity_feed'))
        self.assertEqual(response.status_code, 200)


class CustomLoginViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('logintest', password='pass123')

    def test_login_form_invalid_shows_form(self):
        response = self.client.post(reverse('login'), {'username': 'logintest', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)

    def test_login_form_valid_redirects(self):
        tenant = TenantFactory(slug='t')
        TenantUser.objects.create(user=self.user, tenant=tenant)
        response = self.client.post(reverse('login'), {'username': 'logintest', 'password': 'pass123'})
        self.assertEqual(response.status_code, 302)

    def test_login_sets_single_tenant_in_session(self):
        tenant = TenantFactory(slug='t')
        TenantUser.objects.create(user=self.user, tenant=tenant)
        self.client.post(reverse('login'), {'username': 'logintest', 'password': 'pass123'})
        self.assertIn('tenant_id', self.client.session)

    def test_no_tenant_does_not_set_session(self):
        self.client.post(reverse('login'), {'username': 'logintest', 'password': 'pass123'})
        self.assertNotIn('tenant_id', self.client.session)

    def test_login_multi_tenant_does_not_set_session(self):
        tenant_a = TenantFactory(slug='a')
        tenant_b = TenantFactory(slug='b')
        TenantUser.objects.create(user=self.user, tenant=tenant_a)
        TenantUser.objects.create(user=self.user, tenant=tenant_b)
        self.client.post(reverse('login'), {'username': 'logintest', 'password': 'pass123'})
        self.assertNotIn('tenant_id', self.client.session)

    def test_login_multi_tenant_does_not_set_session(self):
        tenant_a = TenantFactory(slug='a')
        tenant_b = TenantFactory(slug='b')
        TenantUser.objects.create(user=self.user, tenant=tenant_a)
        TenantUser.objects.create(user=self.user, tenant=tenant_b)
        self.client.post('/accounts/login/', {'username': 'logintest', 'password': 'pass123'})
        self.assertNotIn('tenant_id', self.client.session)

    def test_rate_limit_returns_429(self):
        from users.views import CustomLoginView
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(reverse('login'))
        request.limited = True
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.POST = {'username': 'test'}
        request.user = self.user
        view = CustomLoginView()
        view.setup(request)
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 429)


class UserCRUDTenantTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = TenantFactory(slug='a')
        cls.tenant_b = TenantFactory(slug='b')
        cls.tenant_a_user = User.objects.create_user('tenant_a_user', password='pass')
        cls.tenant_b_user = User.objects.create_user('tenant_b_user', password='pass')
        TenantUser.objects.create(user=cls.tenant_a_user, tenant=cls.tenant_a)
        TenantUser.objects.create(user=cls.tenant_b_user, tenant=cls.tenant_b)
        cls.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant_a)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_user_list_filters_by_tenant(self):
        response = self.client.get(reverse('users:user_list'))
        self.assertContains(response, 'tenant_a_user')
        self.assertNotContains(response, 'tenant_b_user')

    def test_user_create_context_has_creating_tenant(self):
        response = self.client.get(reverse('users:user_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('creating_tenant', response.context)
        self.assertEqual(response.context['creating_tenant'], self.tenant_a)

    def test_user_create_with_tenant_creates_tenantuser(self):
        response = self.client.post(reverse('users:user_create'), {
            'username': 'new_tenant_user',
            'password': 'StrongPass123!',
            'is_active': 'on',
            'tenant_role': 'operator',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='new_tenant_user')
        self.assertTrue(TenantUser.objects.filter(user=new_user, tenant=self.tenant_a).exists())

    def test_user_update_other_tenant_returns_404(self):
        response = self.client.get(reverse('users:user_update', kwargs={'pk': self.tenant_b_user.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_delete_other_tenant_returns_404(self):
        response = self.client.post(reverse('users:user_delete', kwargs={'pk': self.tenant_b_user.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_delete_shows_success_message(self):
        response = self.client.post(reverse('users:user_delete', kwargs={'pk': self.tenant_a_user.pk}), follow=True)
        self.assertContains(response, 'exclu')


class GroupedPermissionsTest(TestCase):
    def test_get_grouped_permissions_returns_translated(self):
        from users.views import get_grouped_permissions
        result = get_grouped_permissions()
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_get_grouped_permissions_with_group(self):
        from users.views import get_grouped_permissions
        group = Group.objects.create(name='Test')
        perm = Permission.objects.first()
        group.permissions.add(perm)
        result = get_grouped_permissions(group)
        found = False
        for app, perms in result.items():
            for p in perms:
                if p['id'] == perm.id:
                    self.assertTrue(p['selected'])
                    found = True
        self.assertTrue(found)


class GroupCRUDTenantTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = TenantFactory(slug='a')
        cls.tenant_b = TenantFactory(slug='b')
        cls.admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        TenantUser.objects.create(user=cls.admin, tenant=cls.tenant_a)
        cls.user_a = User.objects.create_user('user_a', password='pass')
        cls.user_b = User.objects.create_user('user_b', password='pass')
        TenantUser.objects.create(user=cls.user_a, tenant=cls.tenant_a)
        TenantUser.objects.create(user=cls.user_b, tenant=cls.tenant_b)
        cls.group_a = Group.objects.create(name='GroupA')
        cls.group_a.user_set.add(cls.user_a)
        cls.group_b = Group.objects.create(name='GroupB')
        cls.group_b.user_set.add(cls.user_b)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_group_list_filters_by_tenant(self):
        response = self.client.get(reverse('users:group_list'))
        self.assertContains(response, 'GroupA')
        self.assertNotContains(response, 'GroupB')

    def test_group_create_context(self):
        response = self.client.get(reverse('users:group_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grouped_permissions', response.context)

    def test_group_update_context(self):
        response = self.client.get(reverse('users:group_update', kwargs={'pk': self.group_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grouped_permissions', response.context)

    def test_group_update_other_tenant_returns_404(self):
        response = self.client.get(reverse('users:group_update', kwargs={'pk': self.group_b.pk}))
        self.assertEqual(response.status_code, 404)

    def test_group_delete_shows_message(self):
        response = self.client.post(reverse('users:group_delete', kwargs={'pk': self.group_a.pk}), follow=True)
        self.assertContains(response, 'eliminado')

    def test_group_delete_other_tenant_returns_404(self):
        response = self.client.post(reverse('users:group_delete', kwargs={'pk': self.group_b.pk}))
        self.assertEqual(response.status_code, 404)


class ProfileEditTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='t')
        cls.user = User.objects.create_user('profileuser', 'p@test.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant)

    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_edit_get_renders_form(self):
        response = self.client.get(reverse('users:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_form', response.context)

    def test_profile_edit_post_valid_redirects(self):
        response = self.client.post(reverse('users:profile_edit'), {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'p@test.com',
            'phone': '',
            'bio': '',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')

    def test_profile_edit_post_invalid_shows_error(self):
        response = self.client.post(reverse('users:profile_edit'), {
            'first_name': 'Updated',
            'email': 'not-an-email',
        })
        self.assertEqual(response.status_code, 200)


class GroupedPermissionsForUserTest(TestCase):
    def test_non_superuser_with_permissions(self):
        from users.views import _get_grouped_permissions_for_user
        user = User.objects.create_user('regular', password='pass')
        perm = Permission.objects.get(codename='view_user')
        user.user_permissions.add(perm)
        result = _get_grouped_permissions_for_user(user)
        self.assertIsInstance(result, dict)

    def test_superuser_returns_all_permissions(self):
        from users.views import _get_grouped_permissions_for_user
        admin = User.objects.create_superuser('admin', 'a@a.com', 'pass')
        result = _get_grouped_permissions_for_user(admin)
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

