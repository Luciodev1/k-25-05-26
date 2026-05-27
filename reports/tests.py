"""Tests for report views: filters, exports, and access control."""
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from brands.models import Brand
from categories.models import Category
from products.models import Product
from customers.models import Customer
from suppliers.models import Supplier
from outflows.models import Outflow, Delivery
from inflows.models import Inflow
from tenants.models import Tenant, TenantUser
from reports.tasks import generate_large_excel_export, generate_large_pdf_export


class ReportAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')

    def test_report_index_requires_login(self):
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 302)

    def test_report_index_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 200)

    def test_outflows_report_requires_login(self):
        response = self.client.get('/reports/outflows-by-customer/')
        self.assertEqual(response.status_code, 302)

    def test_deliveries_report_requires_login(self):
        response = self.client.get('/reports/deliveries/')
        self.assertEqual(response.status_code, 302)

    def test_customer_account_report_requires_login(self):
        response = self.client.get('/reports/customer-account/')
        self.assertEqual(response.status_code, 302)

    def test_supplier_account_report_requires_login(self):
        response = self.client.get('/reports/supplier-account/')
        self.assertEqual(response.status_code, 302)

    def test_balances_report_requires_login(self):
        response = self.client.get('/reports/balances/')
        self.assertEqual(response.status_code, 302)


class ReportContentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('testuser', 'test@test.com', 'testpass123')
        cls.brand = Brand.objects.create(name='Brand')
        cls.category = Category.objects.create(name='Cat')
        cls.customer = Customer.objects.create(name='Customer')
        cls.supplier = Supplier.objects.create(name='Supplier')
        cls.product = Product.objects.create(
            title='Product', category=cls.category, brand=cls.brand,
            cost_price=Decimal('10.00'), selling_price=Decimal('15.00'), quantity=Decimal('100'),
        )

    def test_outflows_report_view(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/outflows-by-customer/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer')

    def test_outflows_report_with_filter(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('5'), price=Decimal('15.00'),
        )
        response = self.client.get(
            f'/reports/outflows-by-customer/?customer={self.customer.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_outflows_report_with_date_filter(self):
        self.client.force_login(self.user)
        today = date.today().isoformat()
        response = self.client.get(
            f'/reports/outflows-by-customer/?start_date={today}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report(self):
        self.client.force_login(self.user)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'))
        response = self.client.get('/reports/deliveries/')
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report_with_status_filter(self):
        self.client.force_login(self.user)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'))
        response = self.client.get('/reports/deliveries/?status=pending')
        self.assertEqual(response.status_code, 200)

    def test_customer_account_report_view(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/customer-account/')
        self.assertEqual(response.status_code, 200)

    def test_customer_account_report_with_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(
            f'/reports/customer-account/?customer={self.customer.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_supplier_account_report_view(self):
        self.client.force_login(self.user)
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10.00'),
        )
        response = self.client.get('/reports/supplier-account/')
        self.assertEqual(response.status_code, 200)

    def test_supplier_account_report_with_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(
            f'/reports/supplier-account/?supplier={self.supplier.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_balances_report_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/balances/')
        self.assertEqual(response.status_code, 200)

    def test_balances_report_with_section(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/balances/?section=customers')
        self.assertEqual(response.status_code, 200)

    def test_balances_report_suppliers_section(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/balances/?section=suppliers')
        self.assertEqual(response.status_code, 200)

    def test_export_excel_outflows(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/outflows-by-customer/?export=excel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_export_pdf_outflows(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/outflows-by-customer/?export=pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_export_excel_deliveries(self):
        self.client.force_login(self.user)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'))
        response = self.client.get('/reports/deliveries/?export=excel')
        self.assertEqual(response.status_code, 200)

    def test_export_pdf_deliveries(self):
        self.client.force_login(self.user)
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'))
        response = self.client.get('/reports/deliveries/?export=pdf')
        self.assertEqual(response.status_code, 200)

    def test_export_excel_customer_account(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/customer-account/?export=excel')
        self.assertEqual(response.status_code, 200)

    def test_export_pdf_customer_account(self):
        self.client.force_login(self.user)
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15.00'),
        )
        response = self.client.get('/reports/customer-account/?export=pdf')
        self.assertEqual(response.status_code, 200)

    def test_export_excel_balances(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/balances/?export=excel')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/vnd.openxmlformats', response['Content-Type'])


class ReportPermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        cls.user = User.objects.create_user('noperm', 'noperm@test.com', 'pass')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')

    def test_report_index_permission_denied(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 403)

    def test_balances_report_permission_denied(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/balances/')
        self.assertEqual(response.status_code, 403)

    def test_task_status_permission_denied(self):
        self.client.force_login(self.user)
        response = self.client.get('/reports/task-status/abc123/')
        self.assertEqual(response.status_code, 403)

    @patch('celery.result.AsyncResult')
    def test_task_status_success(self, mock_async):
        mock_async.return_value.status = 'PENDING'
        mock_async.return_value.ready.return_value = False
        self.client.force_login(self.user)
        perm = Permission.objects.get(codename='view_outflow')
        self.user.user_permissions.add(perm)
        response = self.client.get('/reports/task-status/abc123/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['task_id'], 'abc123')
        self.assertEqual(data['status'], 'PENDING')


class ReportDetailedFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        cls.tenant = Tenant.objects.create(name='T', slug='t')
        TenantUser.objects.create(user=cls.user, tenant=cls.tenant, role='admin')
        cls.brand = Brand.objects.create(name='B')
        cls.cat = Category.objects.create(name='C')
        cls.customer = Customer.objects.create(name='Cust', tenant=cls.tenant)
        cls.supplier = Supplier.objects.create(name='Supp', tenant=cls.tenant)
        cls.product = Product.objects.create(
            title='P', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'), quantity=Decimal('100'),
            tenant=cls.tenant,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_outflows_report_with_tenant_and_product_filter(self):
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        response = self.client.get(
            f'/reports/outflows-by-customer/?product={self.product.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report_with_date_filters(self):
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('10'), tenant=self.tenant)
        today = date.today().isoformat()
        response = self.client.get(
            f'/reports/deliveries/?start_date={today}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report_with_customer_filter(self):
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'), tenant=self.tenant)
        response = self.client.get(
            f'/reports/deliveries/?customer={self.customer.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report_with_product_filter(self):
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'), tenant=self.tenant)
        response = self.client.get(
            f'/reports/deliveries/?product={self.product.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_deliveries_report_delivered_status(self):
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('10'), tenant=self.tenant)
        response = self.client.get('/reports/deliveries/?status=delivered')
        self.assertEqual(response.status_code, 200)

    def test_pending_outflows_in_deliveries(self):
        outflow = Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        Delivery.objects.create(outflow=outflow, quantity=Decimal('5'), tenant=self.tenant)
        response = self.client.get('/reports/deliveries/?status=pending')
        self.assertEqual(response.status_code, 200)

    def test_customer_account_with_date_filters(self):
        Outflow.objects.create(
            product=self.product, customer=self.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=self.tenant,
        )
        today = date.today().isoformat()
        response = self.client.get(
            f'/reports/customer-account/?start_date={today}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)

    def test_customer_account_htmx(self):
        response = self.client.get(
            '/reports/customer-account/', HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)

    def test_supplier_account_with_date_filters(self):
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10'), tenant=self.tenant,
        )
        today = date.today().isoformat()
        response = self.client.get(
            f'/reports/supplier-account/?start_date={today}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)

    def test_supplier_account_export_excel(self):
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10'), tenant=self.tenant,
        )
        response = self.client.get('/reports/supplier-account/?export=excel')
        self.assertEqual(response.status_code, 200)

    def test_supplier_account_export_pdf(self):
        Inflow.objects.create(
            supplier=self.supplier, product=self.product,
            quantity=Decimal('20'), price=Decimal('10'), tenant=self.tenant,
        )
        response = self.client.get('/reports/supplier-account/?export=pdf')
        self.assertEqual(response.status_code, 200)

    def test_balances_pdf_customers_section(self):
        response = self.client.get('/reports/balances/?export=pdf&section=customers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_balances_pdf_suppliers_section(self):
        response = self.client.get('/reports/balances/?export=pdf&section=suppliers')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_balances_pdf_all_section(self):
        response = self.client.get('/reports/balances/?export=pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_balances_with_date_filters(self):
        today = date.today().isoformat()
        response = self.client.get(
            f'/reports/balances/?start_date={today}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)

    def test_balances_excel_suppliers_section(self):
        response = self.client.get('/reports/balances/?export=excel&section=suppliers')
        self.assertEqual(response.status_code, 200)


class ReportTasksTest(TestCase):
    @patch('django.core.files.storage.default_storage')
    @patch('openpyxl.Workbook')
    def test_generate_large_excel_export(self, mock_workbook, mock_storage):
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_workbook.return_value = mock_wb
        mock_wb.active = mock_ws
        mock_model = MagicMock()
        mock_model.objects.filter.return_value.iterator.return_value = [
            MagicMock(pk=1),
            MagicMock(pk=2),
        ]

        with patch('reports.tasks.apps.get_model', return_value=mock_model):
            result = generate_large_excel_export('app.Model', [1, 2], 'test.xlsx')

        self.assertEqual(result['status'], 'ok')
        self.assertIn('exports/', result['path'])
        mock_storage.save.assert_called_once()

    def test_generate_large_pdf_export(self):
        result = generate_large_pdf_export('app.Model', [1, 2, 3], 'test.pdf')
        self.assertEqual(result['status'], 'ok')
        self.assertIn('exports/', result['path'])


class ReportTenantScopedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from tenants.models import Tenant, TenantUser
        cls.tenant_a = Tenant.objects.create(name='A', slug='a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='b')
        cls.user_a = User.objects.create_superuser('usera', 'a@t.com', 'pass')
        cls.user_b = User.objects.create_superuser('userb', 'b@t.com', 'pass')
        TenantUser.objects.create(user=cls.user_a, tenant=cls.tenant_a)
        TenantUser.objects.create(user=cls.user_b, tenant=cls.tenant_b)
        cls.brand = Brand.objects.create(name='BA', tenant=cls.tenant_a)
        cls.cat = Category.objects.create(name='CA', tenant=cls.tenant_a)
        cls.customer = Customer.objects.create(name='CustA', tenant=cls.tenant_a)
        cls.supplier = Supplier.objects.create(name='SuppA', tenant=cls.tenant_a)
        cls.product = Product.objects.create(
            title='PA', category=cls.cat, brand=cls.brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('50'), tenant=cls.tenant_a,
        )
        cls.outflow = Outflow.objects.create(
            product=cls.product, customer=cls.customer,
            quantity=Decimal('10'), price=Decimal('15'), tenant=cls.tenant_a,
        )

    def test_report_outflows_tenant_isolation(self):
        self.client.force_login(self.user_b)
        response = self.client.get('/reports/outflows-by-customer/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'CustA')

    def test_report_balances_tenant_isolation(self):
        self.client.force_login(self.user_b)
        response = self.client.get('/reports/balances/')
        self.assertEqual(response.status_code, 200)

    def test_report_customer_account_tenant_scoped(self):
        self.client.force_login(self.user_a)
        response = self.client.get('/reports/customer-account/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CustA')

    def test_report_supplier_account_tenant_scoped(self):
        self.client.force_login(self.user_a)
        response = self.client.get('/reports/supplier-account/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SuppA')

    def test_report_deliveries_tenant_scoped(self):
        driver = __import__('drivers.models', fromlist=['Driver']).Driver.objects.create(
            name='Drv', phone='123', tenant=self.tenant_a,
        )
        Delivery.objects.create(
            outflow=self.outflow, quantity=Decimal('5'),
            driver=driver, tenant=self.tenant_a,
        )
        self.client.force_login(self.user_a)
        response = self.client.get('/reports/deliveries/')
        self.assertEqual(response.status_code, 200)
