from unittest.mock import MagicMock, patch

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.views.generic import TemplateView

from app.mixins import (
    HtmxMixin, ExportMixin, BulkDeleteMixin, SoftDeleteViewMixin,
)
from brands.models import Brand


class SoftDeleteModelTest(TestCase):
    """Testa SoftDeleteModel através de Brand (modelo real com tabela BD)."""

    def setUp(self):
        self.brand = Brand.objects.create(name='SoftDeleteTestBrand')

    def test_soft_delete_marks_deleted(self):
        self.brand.delete()
        self.assertTrue(self.brand.is_deleted)
        self.assertIsNotNone(self.brand.deleted_at)

    def test_soft_delete_excludes_from_objects(self):
        self.brand.delete()
        self.assertFalse(Brand.objects.filter(pk=self.brand.pk).exists())

    def test_soft_delete_includes_in_all_objects(self):
        self.brand.delete()
        self.assertTrue(Brand.all_objects.filter(pk=self.brand.pk).exists())

    def test_restore_clears_deleted(self):
        self.brand.delete()
        self.brand.restore()
        self.assertFalse(self.brand.is_deleted)
        self.assertIsNone(self.brand.deleted_at)
        self.assertTrue(Brand.objects.filter(pk=self.brand.pk).exists())

    def test_hard_delete_removes(self):
        pk = self.brand.pk
        self.brand.hard_delete()
        self.assertFalse(Brand.all_objects.filter(pk=pk).exists())


class HtmxMixinTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_htmx_request_uses_htmx_template(self):
        class HtmxTestView(HtmxMixin, TemplateView):
            template_name = 'default.html'
            htmx_template_name = 'partial.html'

        request = self.factory.get('/', HTTP_HX_REQUEST='true')
        view = HtmxTestView()
        view.setup(request)
        names = view.get_template_names()
        self.assertEqual(names, ['partial.html'])

    def test_regular_request_uses_default_template(self):
        class HtmxTestView(HtmxMixin, TemplateView):
            template_name = 'default.html'
            htmx_template_name = 'partial.html'

        request = self.factory.get('/')
        view = HtmxTestView()
        view.setup(request)
        names = view.get_template_names()
        self.assertEqual(names, ['default.html'])


class ExportMixinTest(TestCase):
    def setUp(self):
        self.mixin = ExportMixin()
        self.mixin.export_columns = [('Nome', 'name'), ('Valor', 'value')]
        self.mixin.model = MagicMock()
        self.mixin.model._meta.verbose_name_plural = 'Items'

    def test_export_excel_returns_http_response(self):
        mock_brands = [Brand(name='Item1'), Brand(name='Item2')]
        result = self.mixin._export_excel(mock_brands)
        self.assertIsInstance(result, HttpResponse)
        self.assertIn('spreadsheetml', result['Content-Type'])

    def test_export_pdf_returns_http_response(self):
        mock_brands = [Brand(name='Item1'), Brand(name='Item2')]
        result = self.mixin._export_pdf(mock_brands)
        self.assertIsInstance(result, HttpResponse)
        self.assertIn('pdf', result['Content-Type'])


class BulkDeleteMixinTest(TestCase):
    def test_without_permission_raises(self):
        mixin = BulkDeleteMixin()
        mixin.has_delete_permission = MagicMock(return_value=False)
        request = MagicMock()
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            mixin.delete_queryset(request, MagicMock())

    def test_with_permission_calls_super(self):
        mixin = BulkDeleteMixin()
        mixin.has_delete_permission = MagicMock(return_value=True)
        request = MagicMock()
        queryset = MagicMock()
        queryset.count.return_value = 1
        queryset.model._meta.label = 'test.Model'
        with patch.object(BulkDeleteMixin, 'delete_queryset') as mock_super:
            mock_super.side_effect = lambda r, q: None
            result = mixin.delete_queryset(request, queryset)
            mock_super.assert_called()


class SoftDeleteViewMixinTest(TestCase):
    def setUp(self):
        self.mixin = SoftDeleteViewMixin()
        self.factory = RequestFactory()
        self.mock_obj = MagicMock()

    def _add_middleware(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_soft_delete_post_calls_delete(self):
        self.mixin.get_object = MagicMock(return_value=self.mock_obj)
        self.mixin.get_success_url = MagicMock(return_value='/success/')
        request = self.factory.post('/')
        self._add_middleware(request)
        response = self.mixin.post(request)
        self.mock_obj.delete.assert_called_once()
