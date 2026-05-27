from django.test import TestCase
from .models import Category


class CategoryModelTest(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(name='TestCat', description='Test description')
        self.assertEqual(str(cat), 'TestCat')
        self.assertEqual(cat.description, 'Test description')

    def test_category_ordering(self):
        Category.objects.create(name='Zebra')
        Category.objects.create(name='Alpha')
        cats = list(Category.objects.values_list('name', flat=True))
        self.assertEqual(cats, ['Alpha', 'Zebra'])

    def test_category_optional_description(self):
        cat = Category.objects.create(name='NoDesc')
        self.assertIn(cat.description, ('', None))


class CategoryViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='TestCat')

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

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')

