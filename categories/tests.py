from django.test import TestCase
from .models import Category
from tenants.models import Tenant


class CategoryModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='CatsTest', slug='cats-test')

    def test_create_category(self):
        cat = Category.objects.create(name='TestCat', description='Test description', tenant=self.tenant)
        self.assertEqual(str(cat), 'TestCat')
        self.assertEqual(cat.description, 'Test description')

    def test_category_ordering(self):
        Category.objects.create(name='Zebra', tenant=self.tenant)
        Category.objects.create(name='Alpha', tenant=self.tenant)
        cats = list(Category.objects.values_list('name', flat=True))
        self.assertEqual(cats, ['Alpha', 'Zebra'])

    def test_category_optional_description(self):
        cat = Category.objects.create(name='NoDesc', tenant=self.tenant)
        self.assertIn(cat.description, ('', None))


class CategoryViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='CatsTest', slug='cats-test')
        cls.category = Category.objects.create(name='TestCat', tenant=cls.tenant)

    def test_list_requires_login(self):
        response = self.client.get('/categories/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get('/categories/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestCat')

    def test_create_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post('/categories/create/', {'name': 'NewCat', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='NewCat').exists())

    def test_update_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/categories/{self.category.pk}/update/', {'name': 'Updated', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated')

    def test_detail_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get(f'/categories/{self.category.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestCat')

    def test_delete_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/categories/{self.category.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertTrue(self.category.is_deleted)

    def test_trash_view(self):
        self.client.force_login(self._create_user())
        self.category.delete()
        response = self.client.get('/categories/trash/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestCat')

    def test_restore_view(self):
        self.client.force_login(self._create_user())
        self.category.delete()
        response = self.client.post(f'/categories/{self.category.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_deleted)

    def test_hard_delete_view(self):
        self.client.force_login(self._create_user())
        self.category.delete()
        response = self.client.post(f'/categories/{self.category.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.all_objects.filter(pk=self.category.pk).exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')


class CategoryFormTest(TestCase):
    def test_category_form_valid(self):
        from categories.forms import CategoryForm
        form = CategoryForm(data={'name': 'Test', 'description': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_category_form_invalid_empty_name(self):
        from categories.forms import CategoryForm
        form = CategoryForm(data={'name': '', 'description': ''})
        self.assertFalse(form.is_valid())

