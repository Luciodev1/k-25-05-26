"""Tests for product views: CRUD, trash, bulk delete, detail."""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from products.models import Product
from tests.factories import TenantFactory, BrandFactory, CategoryFactory, ProductFactory


class ProductViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='prods-test')
        cls.brand = BrandFactory(name='TestBrand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='TestCategory', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Test Product', category=cls.category, brand=cls.brand,
            tenant=cls.tenant,
        )
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')

    def test_product_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_create_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_create'))
        self.assertEqual(response.status_code, 200)

    def test_product_create_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('products:product_create'), {
            'title': 'New Product',
            'category': self.category.pk,
            'brand': self.brand.pk,
            'cost_price': '20.00',
            'selling_price': '30.00',
            'quantity': '50',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(title='New Product').exists())

    def test_product_update_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_update', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)

    def test_product_update_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('products:product_update', kwargs={'pk': self.product.pk}), {
            'title': 'Updated Product',
            'category': self.category.pk,
            'brand': self.brand.pk,
            'cost_price': '12.00',
            'selling_price': '18.00',
            'quantity': '80',
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.title, 'Updated Product')

    def test_product_delete_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_delete', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)

    def test_product_soft_delete_post(self):
        self.client.force_login(self.user)
        product = ProductFactory(
            title='Del Me', category=self.category, brand=self.brand,
            cost_price=Decimal('5'), selling_price=Decimal('8'), quantity=Decimal('1'),
            tenant=self.tenant,
        )
        response = self.client.post(reverse('products:product_delete', kwargs={'pk': product.pk}))
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertTrue(product.is_deleted)

    def test_product_trash_list(self):
        self.client.force_login(self.user)
        self.product.delete()  # soft-delete
        response = self.client.get(reverse('products:product_trash'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_restore(self):
        self.client.force_login(self.user)
        self.product.delete()
        response = self.client.post(reverse('products:product_restore', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_deleted)

    def test_product_hard_delete(self):
        self.client.force_login(self.user)
        product = ProductFactory(
            title='HardDel', category=self.category, brand=self.brand,
            cost_price=Decimal('5'), selling_price=Decimal('8'), quantity=Decimal('1'),
            tenant=self.tenant,
        )
        product.delete()  # soft-delete first
        response = self.client.post(reverse('products:product_hard_delete', kwargs={'pk': product.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.all_objects.filter(pk=product.pk).exists())

    def test_product_bulk_delete(self):
        self.client.force_login(self.user)
        p2 = ProductFactory(
            title='BulkDel', category=self.category, brand=self.brand,
            cost_price=Decimal('5'), selling_price=Decimal('8'), quantity=Decimal('1'),
            tenant=self.tenant,
        )
        response = self.client.post(reverse('products:product_bulk_delete'), {
            'ids': [self.product.pk, p2.pk],
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)
        p2.refresh_from_db()
        self.assertTrue(p2.is_deleted)

    def test_product_detail_not_found(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, 404)


class ProductFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='prods-test')
        cls.brand = BrandFactory(name='B', tenant=cls.tenant)
        cls.cat = CategoryFactory(name='C', tenant=cls.tenant)
        cls.user = User.objects.create_superuser('admin2', 'a2@t.com', 'pass')

    def test_product_form_valid(self):
        from products.forms import ProductForm
        form = ProductForm(data={
            'title': 'NewP', 'category': self.cat.pk, 'brand': self.brand.pk,
            'cost_price': '10.00', 'selling_price': '15.00', 'quantity': '50',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_product_form_quantity_zero_or_negative(self):
        from products.forms import ProductForm
        for qty in ['0', '-1']:
            form = ProductForm(data={
                'title': 'NewP', 'category': self.cat.pk, 'brand': self.brand.pk,
                'cost_price': '10.00', 'selling_price': '15.00', 'quantity': qty,
            })
            self.assertFalse(form.is_valid())

    def test_export_excel_content_type(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('products:product_list') + '?export=excel')
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_product_form_tenant_filtering(self):
        from products.forms import ProductForm
        tenant = TenantFactory(slug='t')
        tenant_brand = BrandFactory(name='TB', tenant=tenant)
        tenant_cat = CategoryFactory(name='TC', tenant=tenant)
        other_brand = BrandFactory(name='Other')
        other_cat = CategoryFactory(name='Other')
        form = ProductForm(tenant=tenant)
        self.assertIn(tenant_brand, form.fields['brand'].queryset)
        self.assertIn(tenant_cat, form.fields['category'].queryset)
        self.assertNotIn(other_brand, form.fields['brand'].queryset)
        self.assertNotIn(other_cat, form.fields['category'].queryset)
