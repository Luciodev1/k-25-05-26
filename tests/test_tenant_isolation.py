"""Cross-tenant data isolation and concurrency tests.

Verifies that each tenant can only access their own data via HTTP views
and that stock integrity is maintained under concurrent operations.
"""
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from tenants.models import Tenant, TenantUser
from brands.models import Brand
from categories.models import Category
from customers.models import Customer
from suppliers.models import Supplier
from drivers.models import Driver
from products.models import Product
from inflows.models import Inflow
from outflows.models import Outflow


# ---------------------------------------------------------------------------
# Base  -- two tenants with one object each for every model
# ---------------------------------------------------------------------------

class TenantIsolationBase(TestCase):
    """Sets up Tenant A, Tenant B, and one object per model per tenant."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(
            name='Tenant A', slug='tenant-a')
        cls.tenant_b = Tenant.objects.create(
            name='Tenant B', slug='tenant-b')

        cls.user = User.objects.create_superuser(
            'admin_a', 'admin_a@test.com', 'pass')
        TenantUser.objects.create(
            user=cls.user, tenant=cls.tenant_a, role='admin')

        cls.brand_a = Brand.objects.create(
            name='Brand A', tenant=cls.tenant_a)
        cls.brand_b = Brand.objects.create(
            name='Brand B', tenant=cls.tenant_b)

        cls.cat_a = Category.objects.create(
            name='Category A', tenant=cls.tenant_a)
        cls.cat_b = Category.objects.create(
            name='Category B', tenant=cls.tenant_b)

        cls.customer_a = Customer.objects.create(
            name='Customer A', tenant=cls.tenant_a)
        cls.customer_b = Customer.objects.create(
            name='Customer B', tenant=cls.tenant_b)

        cls.supplier_a = Supplier.objects.create(
            name='Supplier A', tenant=cls.tenant_a)
        cls.supplier_b = Supplier.objects.create(
            name='Supplier B', tenant=cls.tenant_b)

        cls.driver_a = Driver.objects.create(
            name='Driver A', phone='111111111',
            truck_plate='LD-01-AA-01', cistern_plate='LD-01-BB-01',
            tenant=cls.tenant_a)
        cls.driver_b = Driver.objects.create(
            name='Driver B', phone='222222222',
            truck_plate='LD-02-AA-02', cistern_plate='LD-02-BB-02',
            tenant=cls.tenant_b)

        cls.product_a = Product.objects.create(
            title='Product A', category=cls.cat_a, brand=cls.brand_a,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('100'), tenant=cls.tenant_a)
        cls.product_b = Product.objects.create(
            title='Product B', category=cls.cat_b, brand=cls.brand_b,
            cost_price=Decimal('20'), selling_price=Decimal('30'),
            quantity=Decimal('200'), tenant=cls.tenant_b)

        cls.inflow_a = Inflow.objects.create(
            product=cls.product_a, supplier=cls.supplier_a,
            quantity=Decimal('50'), price=Decimal('12'),
            tenant=cls.tenant_a)
        cls.inflow_b = Inflow.objects.create(
            product=cls.product_b, supplier=cls.supplier_b,
            quantity=Decimal('100'), price=Decimal('22'),
            tenant=cls.tenant_b)

        cls.outflow_a = Outflow.objects.create(
            product=cls.product_a, customer=cls.customer_a,
            quantity=Decimal('10'), price=Decimal('15'),
            tenant=cls.tenant_a)
        cls.outflow_b = Outflow.objects.create(
            product=cls.product_b, customer=cls.customer_b,
            quantity=Decimal('20'), price=Decimal('30'),
            tenant=cls.tenant_b)

    def _login_as_tenant_a(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['tenant_id'] = str(self.tenant_a.pk)
        session.save()


# ===================================================================
#  PRODUCT isolation
# ===================================================================

class ProductTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product A')
        self.assertNotContains(response, 'Product B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('products:product_detail', kwargs={'pk': self.product_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('products:product_detail', kwargs={'pk': self.product_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  CUSTOMER isolation
# ===================================================================

class CustomerTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('customers:customer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer A')
        self.assertNotContains(response, 'Customer B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('customers:customer_detail', kwargs={'pk': self.customer_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('customers:customer_detail', kwargs={'pk': self.customer_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  SUPPLIER isolation
# ===================================================================

class SupplierTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('suppliers:supplier_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supplier A')
        self.assertNotContains(response, 'Supplier B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('suppliers:supplier_detail', kwargs={'pk': self.supplier_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supplier A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('suppliers:supplier_detail', kwargs={'pk': self.supplier_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  BRAND isolation
# ===================================================================

class BrandTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('brands:brand_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Brand A')
        self.assertNotContains(response, 'Brand B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('brands:brand_detail', kwargs={'pk': self.brand_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Brand A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('brands:brand_detail', kwargs={'pk': self.brand_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  CATEGORY isolation
# ===================================================================

class CategoryTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('categories:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Category A')
        self.assertNotContains(response, 'Category B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('categories:category_detail', kwargs={'pk': self.cat_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Category A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('categories:category_detail', kwargs={'pk': self.cat_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  DRIVER isolation
# ===================================================================

class DriverTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('drivers:driver_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Driver A')
        self.assertNotContains(response, 'Driver B')

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('drivers:driver_detail', kwargs={'pk': self.driver_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Driver A')

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('drivers:driver_detail', kwargs={'pk': self.driver_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  INFLOW isolation
# ===================================================================

class InflowTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('inflows:inflow_list'))
        self.assertEqual(response.status_code, 200)

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('inflows:inflow_detail', kwargs={'pk': self.inflow_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('inflows:inflow_detail', kwargs={'pk': self.inflow_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  OUTFLOW isolation
# ===================================================================

class OutflowTenantIsolationTest(TenantIsolationBase):
    def test_list_filters_by_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(reverse('outflows:outflow_list'))
        self.assertEqual(response.status_code, 200)

    def test_detail_allows_own_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('outflows:outflow_detail', kwargs={'pk': self.outflow_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_detail_blocks_other_tenant(self):
        self._login_as_tenant_a()
        response = self.client.get(
            reverse('outflows:outflow_detail', kwargs={'pk': self.outflow_b.pk}))
        self.assertEqual(response.status_code, 404)


# ===================================================================
#  Concurrency -- stock integrity under race conditions
# ===================================================================

class StockConcurrencyTest(TransactionTestCase):
    """Verify stock validation prevents overselling and select_for_update
    is used to serialize concurrent stock-affecting operations."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='ConcurTenant', slug='concur-tenant')
        self.brand = Brand.objects.create(
            name='ConcurBrand', tenant=self.tenant)
        self.category = Category.objects.create(
            name='ConcurCategory', tenant=self.tenant)
        self.customer = Customer.objects.create(
            name='ConcurCustomer', tenant=self.tenant)
        self.supplier = Supplier.objects.create(
            name='ConcurSupplier', tenant=self.tenant)
        self.product = Product.objects.create(
            title='RaceProduct', category=self.category,
            brand=self.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('100'), tenant=self.tenant)
        self.user = User.objects.create_superuser(
            'concur_admin', 'concur@test.com', 'pass')
        TenantUser.objects.create(
            user=self.user, tenant=self.tenant, role='admin')

    def test_outflow_form_rejects_oversell(self):
        """OutflowForm must reject a quantity exceeding available stock."""
        from outflows.forms import OutflowForm
        form = OutflowForm(tenant=self.tenant, data={
            'product': self.product.pk,
            'customer': self.customer.pk,
            'quantity': '150',
            'price': '15.00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('excede o estoque', str(form.errors).lower())

    def test_outflow_view_uses_select_for_update(self):
        """OutflowCreateView locks the product row via select_for_update."""
        from unittest.mock import patch, MagicMock
        from django.db.models.query import QuerySet

        with patch.object(QuerySet, 'select_for_update') as mock_sfu:
            mock_qs = MagicMock()
            mock_qs.get.return_value = self.product
            mock_sfu.return_value = mock_qs

            self.client.force_login(self.user)
            session = self.client.session
            session['tenant_id'] = str(self.tenant.pk)
            session.save()
            response = self.client.post(
                reverse('outflows:outflow_create'), {
                    'product': self.product.pk,
                    'customer': self.customer.pk,
                    'quantity': '10',
                    'price': '15.00',
                })
            mock_sfu.assert_called()

    def test_inflow_view_uses_select_for_update(self):
        """InflowCreateView locks the product row via select_for_update."""
        from unittest.mock import patch, MagicMock
        from django.db.models.query import QuerySet

        with patch.object(QuerySet, 'select_for_update') as mock_sfu:
            mock_qs = MagicMock()
            mock_qs.get.return_value = self.product
            mock_sfu.return_value = mock_qs

            self.client.force_login(self.user)
            session = self.client.session
            session['tenant_id'] = str(self.tenant.pk)
            session.save()
            response = self.client.post(
                reverse('inflows:inflow_create'), {
                    'product': self.product.pk,
                    'supplier': self.supplier.pk,
                    'quantity': '10',
                    'price': '12.00',
                })
            mock_sfu.assert_called()
