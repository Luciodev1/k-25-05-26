from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user('testuser', 'test@email.com', 'testpass123')
        self.assertEqual(str(user), 'testuser')
        self.assertTrue(user.check_password('testpass123'))

    def test_create_superuser(self):
        admin = User.objects.create_superuser('admin', 'admin@email.com', 'adminpass')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)


class UserViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@email.com', 'adminpass')
        cls.user = User.objects.create_user('testuser', password='testpass123')

    def test_list_requires_login(self):
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 302)

    def test_list_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 403)

    def test_list_view_with_permission(self):
        self.client.force_login(self.admin)
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_create_user_view(self):
        self.client.force_login(self.admin)
        response = self.client.post('/users/create/', {
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
        response = self.client.get('/grupos/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self.admin)
        response = self.client.get('/grupos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestGroup')

    def test_create_group(self):
        self.client.force_login(self.admin)
        response = self.client.post('/grupos/novo/', {'name': 'NewGroup', 'permissions': []})
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
        response = self.client.get('/perfil/')
        self.assertEqual(response.status_code, 302)

    def test_profile_view_for_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/perfil/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meu Perfil')
        self.assertContains(response, 'Administrador')
        self.assertContains(response, 'adminuser')

    def test_profile_view_for_manager_group(self):
        self.client.force_login(self.manager_user)
        response = self.client.get('/perfil/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerente')
        self.assertContains(response, 'manageruser')

    def test_profile_view_for_operator_fallback(self):
        self.client.force_login(self.basic_user)
        response = self.client.get('/perfil/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operador')
        self.assertContains(response, 'regularuser')

    def test_reports_index_requires_permissions(self):
        # Sem nenhuma permissão relevante
        self.client.force_login(self.basic_user)
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 403)

        # Com permissão relacionada (mas sem tenant, continua bloqueado)
        view_outflow = Permission.objects.get(codename='view_outflow')
        self.basic_user.user_permissions.add(view_outflow)
        
        user_with_perm = User.objects.get(id=self.basic_user.id)
        self.client.force_login(user_with_perm)
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 403)

    def test_specific_reports_restricted(self):
        self.client.force_login(self.basic_user)
        
        # Outflows Report
        response = self.client.get('/reports/outflows-by-customer/')
        self.assertEqual(response.status_code, 403)
        
        # Deliveries Report
        response = self.client.get('/reports/deliveries/')
        self.assertEqual(response.status_code, 403)

        # Customer Account Report
        response = self.client.get('/reports/customer-account/')
        self.assertEqual(response.status_code, 403)

        # Supplier Account Report
        response = self.client.get('/reports/supplier-account/')
        self.assertEqual(response.status_code, 403)

        # Balances Report
        response = self.client.get('/reports/balances/')
        self.assertEqual(response.status_code, 403)

    def test_specific_reports_accessible_with_perms(self):
        view_outflow = Permission.objects.get(codename='view_outflow')
        self.basic_user.user_permissions.add(view_outflow)
        user_with_perm = User.objects.get(id=self.basic_user.id)
        self.client.force_login(user_with_perm)

        # Utilizador sem tenant associado — acesso negado mesmo com permissão
        response = self.client.get('/reports/outflows-by-customer/')
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get('/reports/deliveries/')
        self.assertEqual(response.status_code, 403)

    def test_audit_logs_restricted_to_authorized_only(self):
        self.client.force_login(self.basic_user)
        
        response = self.client.get('/auditoria/')
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get('/atividade/')
        self.assertEqual(response.status_code, 403)

    def test_audit_logs_accessible_for_superuser(self):
        self.client.force_login(self.superuser)
        
        response = self.client.get('/auditoria/')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/atividade/')
        self.assertEqual(response.status_code, 200)

