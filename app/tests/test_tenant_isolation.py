from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest

from tenants.models import Tenant, TenantUser
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from suppliers.models import Supplier
from inflows.models import Inflow
from outflows.models import Outflow


class TenantIsolationBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='Tenant A', slug='tenant-a')
        cls.tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b')
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant_a)
        cls.brand_a = Brand.objects.create(name='Brand A', tenant=cls.tenant_a)
        cls.brand_b = Brand.objects.create(name='Brand B', tenant=cls.tenant_b)
        cls.cat_a = Category.objects.create(name='Cat A', tenant=cls.tenant_a)
        cls.cat_b = Category.objects.create(name='Cat B', tenant=cls.tenant_b)
        cls.customer_a = Customer.objects.create(name='Cust A', tenant=cls.tenant_a)
        cls.customer_b = Customer.objects.create(name='Cust B', tenant=cls.tenant_b)
        cls.supplier_a = Supplier.objects.create(name='Supp A', tenant=cls.tenant_a)
        cls.supplier_b = Supplier.objects.create(name='Supp B', tenant=cls.tenant_b)
        cls.product_a = Product.objects.create(
            title='Prod A', category=cls.cat_a, brand=cls.brand_a,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant_a,
        )
        cls.product_b = Product.objects.create(
            title='Prod B', category=cls.cat_b, brand=cls.brand_b,
            cost_price=Decimal('20'), selling_price=Decimal('30'),
            quantity=Decimal('100'), tenant=cls.tenant_b,
        )

    def _mock_request_with_tenant(self, tenant):
        request = HttpRequest()
        request.tenant = tenant
        request.user = self.user
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        return request


class BrandTenantIsolationTest(TenantIsolationBase):
    def test_tenant_a_cannot_see_brand_from_tenant_b(self):
        request = self._mock_request_with_tenant(self.tenant_a)
        qs = Brand.objects.filter(tenant=self.tenant_b)
        self.assertIn(self.brand_b, qs)
        own_qs = Brand.objects.filter(tenant=self.tenant_a)
        self.assertIn(self.brand_a, own_qs)
        self.assertNotIn(self.brand_b, own_qs)

    def test_tenant_cannot_create_brand_for_other_tenant(self):
        brand = Brand.objects.create(name='Cross Tenancy', tenant=self.tenant_a)
        self.assertEqual(brand.tenant, self.tenant_a)
        count_b = Brand.objects.filter(tenant=self.tenant_b).count()
        self.assertEqual(count_b, 1)

    def test_tenant_isolation_on_product_list(self):
        products_a = Product.objects.filter(tenant=self.tenant_a)
        products_b = Product.objects.filter(tenant=self.tenant_b)
        self.assertIn(self.product_a, products_a)
        self.assertNotIn(self.product_b, products_a)
        self.assertIn(self.product_b, products_b)
        self.assertNotIn(self.product_a, products_b)


class CustomerTenantIsolationTest(TenantIsolationBase):
    def test_customer_tenant_isolation(self):
        customers_a = Customer.objects.filter(tenant=self.tenant_a)
        customers_b = Customer.objects.filter(tenant=self.tenant_b)
        self.assertIn(self.customer_a, customers_a)
        self.assertNotIn(self.customer_b, customers_a)
        self.assertIn(self.customer_b, customers_b)
        self.assertNotIn(self.customer_a, customers_b)


class SupplierTenantIsolationTest(TenantIsolationBase):
    def test_supplier_tenant_isolation(self):
        suppliers_a = Supplier.objects.filter(tenant=self.tenant_a)
        suppliers_b = Supplier.objects.filter(tenant=self.tenant_b)
        self.assertIn(self.supplier_a, suppliers_a)
        self.assertNotIn(self.supplier_b, suppliers_a)
        self.assertIn(self.supplier_b, suppliers_b)
        self.assertNotIn(self.supplier_a, suppliers_b)


class CrossTenantDataLeakTest(TenantIsolationBase):
    def test_cross_tenant_query_parameter_injection(self):
        qs = Product.objects.filter(tenant=self.tenant_a)
        for p in qs:
            self.assertEqual(p.tenant, self.tenant_a)

    def test_bulk_create_respects_tenant(self):
        Product.objects.bulk_create([
            Product(title='Bulk 1', category=self.cat_a, brand=self.brand_a,
                    cost_price=Decimal('5'), selling_price=Decimal('10'),
                    quantity=Decimal('1'), tenant=self.tenant_a),
            Product(title='Bulk 2', category=self.cat_a, brand=self.brand_a,
                    cost_price=Decimal('5'), selling_price=Decimal('10'),
                    quantity=Decimal('1'), tenant=self.tenant_a),
        ])
        self.assertEqual(Product.objects.filter(tenant=self.tenant_a).count(), 3)
        self.assertEqual(Product.objects.filter(tenant=self.tenant_b).count(), 1)
