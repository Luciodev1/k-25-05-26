from unittest.mock import MagicMock, patch

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError

from app.mixins import (
    HtmxMixin, ExportMixin, BulkDeleteMixin, SoftDeleteViewMixin,
    FinanceiroRequiredMixin, GestorRequiredMixin, AdminRequiredMixin,
    TenantFilterMixin, TenantCreateMixin,
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from brands.models import Brand
from tenants.models import Tenant


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


class FinanceiroRequiredMixinTest(TestCase):
    def test_handle_no_permission_raises_denied(self):
        mixin = FinanceiroRequiredMixin()
        with self.assertRaises(PermissionDenied):
            mixin.handle_no_permission()


class GestorRequiredMixinTest(TestCase):
    def test_handle_no_permission_raises_denied(self):
        mixin = GestorRequiredMixin()
        with self.assertRaises(PermissionDenied):
            mixin.handle_no_permission()


class AdminRequiredMixinTest(TestCase):
    def test_handle_no_permission_raises_denied(self):
        mixin = AdminRequiredMixin()
        with self.assertRaises(PermissionDenied):
            mixin.handle_no_permission()


class _BaseGetQuerysetView:
    def get_queryset(self):
        return Brand.objects.all()

class _BaseFormValidView:
    def form_valid(self, form):
        return HttpResponse()


class TenantFilterMixinTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')

    def test_get_queryset_with_tenant_filters(self):
        class _ConcreteView(TenantFilterMixin, _BaseGetQuerysetView):
            pass
        request = MagicMock()
        request.tenant = self.tenant
        view = _ConcreteView()
        view.request = request
        qs = view.get_queryset()
        self.assertQuerySetEqual(qs, [])

    def test_get_queryset_without_tenant_returns_all(self):
        class _ConcreteView(TenantFilterMixin, _BaseGetQuerysetView):
            pass
        request = MagicMock()
        request.tenant = None
        view = _ConcreteView()
        view.request = request
        qs = view.get_queryset()
        self.assertQuerySetEqual(qs, [])

    def test_form_valid_sets_tenant_on_instance(self):
        class _ConcreteView(TenantFilterMixin, _BaseFormValidView):
            pass
        request = MagicMock()
        request.tenant = self.tenant
        form = MagicMock()
        form.instance = Brand()
        view = _ConcreteView()
        view.request = request
        response = view.form_valid(form)
        self.assertEqual(form.instance.tenant, self.tenant)

    def test_form_valid_no_tenant_skips_set(self):
        class _ConcreteView(TenantFilterMixin, _BaseFormValidView):
            pass
        request = MagicMock()
        request.tenant = None
        form = MagicMock()
        form.instance = Brand()
        view = _ConcreteView()
        view.request = request
        response = view.form_valid(form)
        self.assertIsNone(form.instance.tenant_id)


class _BaseGetInitialView:
    def get_initial(self):
        return {}


class TenantCreateMixinTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Test Tenant', slug='test-tenant')

    def test_get_initial_includes_tenant(self):
        class _ConcreteView(TenantCreateMixin, _BaseGetInitialView):
            pass
        request = MagicMock()
        request.tenant = self.tenant
        view = _ConcreteView()
        view.request = request
        view.model = Brand
        initial = view.get_initial()
        self.assertEqual(initial['tenant'], self.tenant)

    def test_get_initial_without_tenant(self):
        class _ConcreteView(TenantCreateMixin, _BaseGetInitialView):
            pass
        request = MagicMock()
        request.tenant = None
        view = _ConcreteView()
        view.request = request
        view.model = Brand
        initial = view.get_initial()
        self.assertNotIn('tenant', initial)


class BaseListViewTest(TestCase):
    def test_class_attributes(self):
        self.assertEqual(BaseListView.paginate_by, 10)

    def test_mro_includes_mixins(self):
        self.assertIn(HtmxMixin, BaseListView.__mro__)
        self.assertIn(ExportMixin, BaseListView.__mro__)
        self.assertIn(TenantFilterMixin, BaseListView.__mro__)


class BaseCreateViewTest(TestCase):
    def test_mro_includes_mixins(self):
        self.assertIn(TenantCreateMixin, BaseCreateView.__mro__)


class BaseUpdateViewTest(TestCase):
    def test_mro_includes_mixins(self):
        self.assertIn(TenantFilterMixin, BaseUpdateView.__mro__)


class BaseDetailViewTest(TestCase):
    def test_mro_includes_mixins(self):
        self.assertIn(TenantFilterMixin, BaseDetailView.__mro__)


class BaseDeleteViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.brand = Brand.objects.create(name='DeleteTestBrand')

    def _add_middleware(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_post_deletes_and_redirects(self):
        view = BaseDeleteView()
        view.model = Brand
        view.success_message = 'Deleted'
        view.get_object = MagicMock(return_value=self.brand)
        view.get_success_url = MagicMock(return_value='/success/')
        request = self.factory.post('/')
        self._add_middleware(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brand.all_objects.get(pk=self.brand.pk).is_deleted)

    def test_post_protected_error_shows_message(self):
        view = BaseDeleteView()
        view.model = Brand
        view.get_object = MagicMock(side_effect=ProtectedError('protected', self.brand))
        view.get_success_url = MagicMock(return_value='/success/')
        request = self.factory.post('/')
        self._add_middleware(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 302)


class BaseTrashListViewTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.brand = Brand.objects.create(name='Active')
        self.deleted = Brand.objects.create(name='Deleted')
        self.deleted.delete()

    def test_get_queryset_returns_only_deleted(self):
        view = BaseTrashListView()
        view.model = Brand
        view.request = MagicMock()
        view.request.tenant = None
        qs = view.get_queryset()
        self.assertIn(self.deleted, qs)
        self.assertNotIn(self.brand, qs)

    def test_get_queryset_filters_by_tenant(self):
        tenant2 = Tenant.objects.create(name='T2', slug='t2')
        deleted_other = Brand.objects.create(name='OtherDeleted', tenant=tenant2)
        deleted_other.delete()
        view = BaseTrashListView()
        view.model = Brand
        view.request = MagicMock()
        view.request.tenant = self.tenant
        qs = view.get_queryset()
        self.assertNotIn(deleted_other, qs)


class BaseRestoreViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.brand = Brand.objects.create(name='RestoreTest', tenant=self.tenant)
        self.brand.delete()
        self.view = BaseRestoreView()
        self.view.model = Brand
        self.view.redirect_url = '/success/'
        self.view.success_message = 'Restored'

    def _add_middleware(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_post_restores_object(self):
        request = self.factory.post('/')
        request.tenant = self.tenant
        self._add_middleware(request)
        response = self.view.post(request, pk=self.brand.pk)
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertFalse(self.brand.is_deleted)

    def test_post_wrong_tenant_shows_error(self):
        other_tenant = Tenant.objects.create(name='Other', slug='other')
        request = self.factory.post('/')
        request.tenant = other_tenant
        self._add_middleware(request)
        response = self.view.post(request, pk=self.brand.pk)
        self.assertEqual(response.status_code, 302)
        self.brand.refresh_from_db()
        self.assertTrue(self.brand.is_deleted)


class BaseHardDeleteViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.brand = Brand.objects.create(name='HardDeleteTest', tenant=self.tenant)
        self.brand.delete()
        self.view = BaseHardDeleteView()
        self.view.model = Brand
        self.view.redirect_url = '/success/'
        self.view.success_message = 'HardDeleted'

    def _add_middleware(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_post_hard_deletes_object(self):
        pk = self.brand.pk
        request = self.factory.post('/')
        request.tenant = self.tenant
        self._add_middleware(request)
        response = self.view.post(request, pk=pk)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Brand.all_objects.filter(pk=pk).exists())

    def test_post_wrong_tenant_does_not_delete(self):
        other_tenant = Tenant.objects.create(name='Other', slug='other')
        pk = self.brand.pk
        request = self.factory.post('/')
        request.tenant = other_tenant
        self._add_middleware(request)
        response = self.view.post(request, pk=pk)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brand.all_objects.filter(pk=pk).exists())


class ExportMixinGetTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mixin = ExportMixin()
        self.mixin.export_columns = [('Nome', 'name')]
        self.mixin.model = MagicMock()
        self.mixin.model._meta.verbose_name_plural = 'Items'
        self.mixin.get_queryset = MagicMock(return_value=[Brand(name='X')])

    def test_get_with_export_excel(self):
        request = self.factory.get('/?export=excel')
        with patch.object(ExportMixin, '_export_excel', return_value=HttpResponse('excel')):
            result = self.mixin.get(request)
        self.assertEqual(result.content, b'excel')

    def test_get_with_export_pdf(self):
        request = self.factory.get('/?export=pdf')
        with patch.object(ExportMixin, '_export_pdf', return_value=HttpResponse('pdf')):
            result = self.mixin.get(request)
        self.assertEqual(result.content, b'pdf')

    def test_get_without_export_calls_super(self):
        request = self.factory.get('/')
        with patch.object(ExportMixin, 'get', return_value=HttpResponse('normal')) as mock_super:
            result = mock_super(request)
        self.assertEqual(result.content, b'normal')
