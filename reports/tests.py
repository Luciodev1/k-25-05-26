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
