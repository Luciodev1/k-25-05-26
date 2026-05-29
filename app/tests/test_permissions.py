from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

from app.mixins import (
    FinanceiroRequiredMixin, GestorRequiredMixin, AdminRequiredMixin,
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseRestoreView, BaseHardDeleteView,
)
from tenants.models import Tenant, TenantUser
from brands.models import Brand
from payments.models import Payment
from products.models import Product


class PermissionMixinBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='PermTest', slug='perm-test')

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('user', 'u@t.com', 'pass')
        self.superuser = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        self.brand = Brand.objects.create(name='TestBrand', tenant=self.tenant)

    def _add_middleware(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def _get_perm(self, codename, model=None):
        if model is None:
            model = Brand
        ct = ContentType.objects.get_for_model(model)
        return Permission.objects.get(codename=codename, content_type=ct)


class FinanceiroRequiredMixinTest(PermissionMixinBase):
    def test_anonymous_has_no_permission(self):
        mixin = FinanceiroRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = AnonymousUser()
        self.assertFalse(mixin.has_permission())

    def test_user_without_permission_has_no_permission(self):
        mixin = FinanceiroRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertFalse(mixin.has_permission())

    def test_user_with_permission_has_permission(self):
        perm = self._get_perm('add_payment', Payment)
        self.user.user_permissions.add(perm)
        mixin = FinanceiroRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertTrue(mixin.has_permission())


class GestorRequiredMixinTest(PermissionMixinBase):
    def test_user_without_permission_has_no_permission(self):
        mixin = GestorRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertFalse(mixin.has_permission())

    def test_user_with_both_permissions_has_permission(self):
        for codename in ('add_product', 'change_product'):
            perm = self._get_perm(codename, Product)
            self.user.user_permissions.add(perm)
        mixin = GestorRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertTrue(mixin.has_permission())

    def test_user_with_partial_permissions_has_no_permission(self):
        perm = self._get_perm('add_product', Product)
        self.user.user_permissions.add(perm)
        mixin = GestorRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertFalse(mixin.has_permission())


class AdminRequiredMixinTest(PermissionMixinBase):
    def test_user_without_permission_has_no_permission(self):
        mixin = AdminRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.user
        self.assertFalse(mixin.has_permission())

    def test_superuser_has_permission(self):
        mixin = AdminRequiredMixin()
        mixin.request = self.factory.get('/')
        mixin.request.user = self.superuser
        self.assertTrue(mixin.has_permission())


class BaseViewsPermissionTest(PermissionMixinBase):
    def test_list_view_requires_permission(self):
        self.assertTrue(hasattr(BaseListView, 'permission_required'))

    def test_create_view_requires_permission(self):
        self.assertTrue(hasattr(BaseCreateView, 'permission_required'))

    def test_update_view_requires_permission(self):
        self.assertTrue(hasattr(BaseUpdateView, 'permission_required'))

    def test_detail_view_requires_permission(self):
        self.assertTrue(hasattr(BaseDetailView, 'permission_required'))

    def test_delete_view_requires_permission(self):
        self.assertTrue(hasattr(BaseDeleteView, 'permission_required'))

    def test_restore_view_requires_permission(self):
        self.assertTrue(hasattr(BaseRestoreView, 'permission_required'))

    def test_hard_delete_view_requires_permission(self):
        self.assertTrue(hasattr(BaseHardDeleteView, 'permission_required'))
