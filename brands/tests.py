from django.test import TestCase
from .models import Brand
from tenants.models import Tenant


class BrandModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='BrandsTest', slug='brands-test')

    def test_create_brand(self):
        brand = Brand.objects.create(name='TestBrand', description='Test description', tenant=self.tenant)
        self.assertEqual(str(brand), 'TestBrand')
        self.assertEqual(brand.description, 'Test description')

    def test_brand_ordering(self):
        Brand.objects.create(name='Zebra', tenant=self.tenant)
        Brand.objects.create(name='Alpha', tenant=self.tenant)
        brands = list(Brand.objects.values_list('name', flat=True))
        self.assertEqual(brands, ['Alpha', 'Zebra'])

    def test_brand_optional_description(self):
        brand = Brand.objects.create(name='NoDesc', tenant=self.tenant)
        self.assertIn(brand.description, ('', None))


class BrandViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='BrandsViewTest', slug='brands-view-test')
        cls.brand = Brand.objects.create(name='TestBrand', tenant=cls.tenant)

    def test_list_requires_login(self):
        response = self.client.get('/brands/list/')
        self.assertEqual(response.status_code, 302)

    def test_list_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get('/brands/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestBrand')

    def test_create_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post('/brands/create/', {'name': 'NewBrand', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brand.objects.filter(name='NewBrand').exists())

    def test_update_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/brands/{self.brand.pk}/update/', {'name': 'Updated', 'description': ''})
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.name, 'Updated')

    def test_detail_view(self):
        self.client.force_login(self._create_user())
        response = self.client.get(f'/brands/{self.brand.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestBrand')

    def test_delete_view(self):
        self.client.force_login(self._create_user())
        response = self.client.post(f'/brands/{self.brand.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertTrue(self.brand.is_deleted)

    def test_delete_requires_permission(self):
        user = self._create_user()
        user.is_superuser = False
        user.save()
        self.client.force_login(user)
        response = self.client.post(f'/brands/{self.brand.pk}/delete/')
        self.assertEqual(response.status_code, 403)

    def test_trash_view(self):
        self.client.force_login(self._create_user())
        self.brand.delete()
        response = self.client.get('/brands/trash/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TestBrand')

    def test_restore_view(self):
        self.client.force_login(self._create_user())
        self.brand.delete()
        response = self.client.post(f'/brands/{self.brand.pk}/restore/')
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertFalse(self.brand.is_deleted)

    def test_hard_delete_view(self):
        self.client.force_login(self._create_user())
        self.brand.delete()
        response = self.client.post(f'/brands/{self.brand.pk}/hard-delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Brand.all_objects.filter(pk=self.brand.pk).exists())

    def _create_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')


class BrandFormTest(TestCase):
    def test_brand_form_valid(self):
        from brands.forms import BrandForm
        form = BrandForm(data={'name': 'Test', 'description': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_brand_form_invalid_empty_name(self):
        from brands.forms import BrandForm
        form = BrandForm(data={'name': '', 'description': ''})
        self.assertFalse(form.is_valid())
