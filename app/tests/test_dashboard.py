"""Tests for dashboard view and error handlers."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from suppliers.models import Supplier
from inflows.models import Inflow
from outflows.models import Outflow
from tenants.models import Tenant, TenantUser


class DashboardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='DashTest', slug='dash-test')
        cls.user = User.objects.create_superuser('admin', 'admin@test.com', 'adminpass')
        cls.brand = Brand.objects.create(name='Brand', tenant=cls.tenant)
        cls.category = Category.objects.create(name='Cat', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Customer', tenant=cls.tenant)
        cls.supplier = Supplier.objects.create(name='Supplier', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'),
            quantity=Decimal('50'), tenant=cls.tenant,
        )
        Product.objects.create(
            title='LowStock', category=cls.category, brand=cls.brand,
            cost_price=Decimal('5.00'), selling_price=Decimal('8.00'),
            quantity=Decimal('3'), tenant=cls.tenant,
        )
        Inflow.objects.create(
            product=cls.product, supplier=cls.supplier,
            quantity=Decimal('20'), price=Decimal('10.00'), tenant=cls.tenant,
        )
        Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('5'), price=Decimal('15.00'), tenant=cls.tenant,
        )
        Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15.00'), tenant=cls.tenant,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')

    def test_dashboard_context_data(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        ctx = response.context
        self.assertEqual(ctx['total_products'], 2)
        self.assertEqual(ctx['total_suppliers'], 1)
        self.assertEqual(ctx['total_customers'], 1)
        self.assertEqual(ctx['inflows_this_month'], 1)
        self.assertEqual(ctx['outflows_this_month'], 2)
        self.assertEqual(len(ctx['outflows_pending']), 2)  # both undelivered
        self.assertGreater(ctx['total_stock_value'], Decimal('0'))
        self.assertIsInstance(ctx['margin_pct'], (int, float, Decimal))
        self.assertEqual(len(ctx['recent_inflows']), 1)
        self.assertEqual(len(ctx['recent_outflows']), 2)
        self.assertEqual(len(ctx['low_stock_products']), 1)
        self.assertEqual(len(ctx['top_customers']), 1)
        self.assertEqual(len(ctx['outflows_pending']), 2)

    def test_dashboard_no_data(self):
        Inflow.objects.all().delete()
        Outflow.objects.all().delete()
        Product.objects.all().delete()
        Customer.objects.all().delete()
        Supplier.objects.all().delete()
        user = User.objects.create_superuser('fresh', 'f@t.com', 'pass')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertEqual(ctx['total_products'], 0)
        self.assertEqual(ctx['margin_pct'], Decimal('0'))

    def test_404_handler(self):
        response = self.client.get('/nonexistent-page-xyz/')
        self.assertEqual(response.status_code, 404)

    def test_custom_404_rendered(self):
        # Turn off DEBUG-like handling by using the handler
        response = self.client.get('/nonexistent-page-xyz/')
        self.assertContains(response, '404', status_code=404)


class ErrorHandlerTest(TestCase):
    def test_404_page(self):
        response = self.client.get('/this-page-does-not-exist-999/')
        self.assertEqual(response.status_code, 404)


class DashboardTenantScopedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant)
        cls.brand = Brand.objects.create(name='B', tenant=cls.tenant)
        cls.cat = Category.objects.create(name='C', tenant=cls.tenant)
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.supplier = Supplier.objects.create(name='Supp', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant,
        )
        Inflow.objects.create(
            product=cls.product, supplier=cls.supplier,
            quantity=Decimal('20'), price=Decimal('10'), tenant=cls.tenant,
        )
        Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('5'), price=Decimal('15'), tenant=cls.tenant,
        )

    def test_dashboard_with_tenant(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_products'], 1)
        self.assertEqual(response.context['total_suppliers'], 1)
