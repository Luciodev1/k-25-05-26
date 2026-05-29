"""Tests for permission enforcement across all views."""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from tenants.models import TenantUser
from tests.factories import (
    TenantFactory,
    BrandFactory,
    CategoryFactory,
    ProductFactory,
    SupplierFactory,
    InflowFactory,
    CustomerFactory,
    OutflowFactory,
)


class UnauthenticatedAccessTest(TestCase):
    """1. Unauthenticated users cannot access any view."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='unauth-test')
        cls.brand = BrandFactory(name='UnauthBrand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='UnauthCat', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Unauth Product', category=cls.category, brand=cls.brand,
            tenant=cls.tenant,
        )
        cls.supplier = SupplierFactory(tenant=cls.tenant)
        cls.customer = CustomerFactory(tenant=cls.tenant)
        cls.inflow = InflowFactory(
            product=cls.product, supplier=cls.supplier, tenant=cls.tenant,
        )
        cls.outflow = OutflowFactory(
            product=cls.product, customer=cls.customer, tenant=cls.tenant,
        )

    # ── Products ──────────────────────────────────────────────────────
    # Views with LoginRequiredMixin redirect (302).
    # GestorRequiredMixin overrides handle_no_permission → 403.

    def test_unauth_product_list(self):
        self.assertEqual(
            self.client.get(reverse('products:product_list')).status_code, 302,
        )

    def test_unauth_product_detail(self):
        self.assertEqual(
            self.client.get(
                reverse('products:product_detail', kwargs={'pk': self.product.pk}),
            ).status_code, 302,
        )

    def test_unauth_product_create(self):
        self.assertEqual(
            self.client.get(reverse('products:product_create')).status_code, 403,
        )

    def test_unauth_product_update(self):
        self.assertEqual(
            self.client.get(
                reverse('products:product_update', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_unauth_product_delete(self):
        self.assertEqual(
            self.client.get(
                reverse('products:product_delete', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_unauth_product_bulk_delete(self):
        self.assertEqual(
            self.client.post(
                reverse('products:product_bulk_delete'), {'ids': []},
            ).status_code, 403,
        )

    def test_unauth_product_trash(self):
        self.assertEqual(
            self.client.get(reverse('products:product_trash')).status_code, 302,
        )

    def test_unauth_product_restore(self):
        self.assertEqual(
            self.client.post(
                reverse('products:product_restore', kwargs={'pk': self.product.pk}),
            ).status_code, 302,
        )

    def test_unauth_product_hard_delete(self):
        self.assertEqual(
            self.client.post(
                reverse('products:product_hard_delete', kwargs={'pk': self.product.pk}),
            ).status_code, 302,
        )

    # ── Inflows ───────────────────────────────────────────────────────

    def test_unauth_inflow_list(self):
        self.assertEqual(
            self.client.get(reverse('inflows:inflow_list')).status_code, 302,
        )

    def test_unauth_inflow_create(self):
        self.assertEqual(
            self.client.get(reverse('inflows:inflow_create')).status_code, 302,
        )

    def test_unauth_inflow_detail(self):
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_detail', kwargs={'pk': self.inflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_inflow_update(self):
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_update', kwargs={'pk': self.inflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_inflow_delete(self):
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_delete', kwargs={'pk': self.inflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_inflow_trash(self):
        self.assertEqual(
            self.client.get(reverse('inflows:inflow_trash')).status_code, 302,
        )

    def test_unauth_inflow_restore(self):
        self.assertEqual(
            self.client.post(
                reverse('inflows:inflow_restore', kwargs={'pk': self.inflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_inflow_hard_delete(self):
        self.assertEqual(
            self.client.post(
                reverse('inflows:inflow_hard_delete', kwargs={'pk': self.inflow.pk}),
            ).status_code, 302,
        )

    # ── Outflows ──────────────────────────────────────────────────────

    def test_unauth_outflow_list(self):
        self.assertEqual(
            self.client.get(reverse('outflows:outflow_list')).status_code, 302,
        )

    def test_unauth_outflow_create(self):
        self.assertEqual(
            self.client.get(reverse('outflows:outflow_create')).status_code, 302,
        )

    def test_unauth_outflow_detail(self):
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_detail', kwargs={'pk': self.outflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_outflow_update(self):
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_update', kwargs={'pk': self.outflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_outflow_delete(self):
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_delete', kwargs={'pk': self.outflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_outflow_trash(self):
        self.assertEqual(
            self.client.get(reverse('outflows:outflow_trash')).status_code, 302,
        )

    def test_unauth_outflow_restore(self):
        self.assertEqual(
            self.client.post(
                reverse('outflows:outflow_restore', kwargs={'pk': self.outflow.pk}),
            ).status_code, 302,
        )

    def test_unauth_outflow_hard_delete(self):
        self.assertEqual(
            self.client.post(
                reverse('outflows:outflow_hard_delete', kwargs={'pk': self.outflow.pk}),
            ).status_code, 302,
        )


class AuthPermissionTestBase(TestCase):
    """Base class providing tenant-aware user creation."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = TenantFactory(slug='perm-base')
        cls.brand = BrandFactory(name='AuthBrand', tenant=cls.tenant)
        cls.category = CategoryFactory(name='AuthCat', tenant=cls.tenant)
        cls.product = ProductFactory(
            title='Auth Product', category=cls.category,
            brand=cls.brand, tenant=cls.tenant,
        )

    def _create_user(self, username, permissions=None):
        user = User.objects.create_user(username, f'{username}@t.com', 'pass')
        for perm in (permissions or []):
            user.user_permissions.add(Permission.objects.get(codename=perm))
        TenantUser.objects.create(
            user=user, tenant=self.tenant, role='operator', is_primary=True,
        )
        return user

    def _login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['tenant_id'] = str(self.tenant.id)
        session.save()


class ViewProductPermissionTest(AuthPermissionTestBase):
    """2 & 3. Users without/with view_product permission."""

    # ── Without view_product → 403 ────────────────────────────────────

    def test_list_without_view(self):
        user = self._create_user('nolistview')
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_list')).status_code, 403,
        )

    def test_detail_without_view(self):
        user = self._create_user('nodetailview')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_detail', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    # ── With view_product → 200 ───────────────────────────────────────

    def test_list_with_view(self):
        user = self._create_user('withlistview', ['view_product'])
        self._login(user)
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Auth Product')

    def test_detail_with_view(self):
        user = self._create_user('withdetailview', ['view_product'])
        self._login(user)
        response = self.client.get(
            reverse('products:product_detail', kwargs={'pk': self.product.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Auth Product')


class CreateUpdateDeletePermissionTest(AuthPermissionTestBase):
    """4. Create / Update / Delete permission enforcement."""

    # ── Product create (GestorRequiredMixin → add_product + change_product) ─

    def test_create_without_perms(self):
        user = self._create_user('crno')
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_create')).status_code, 403,
        )

    def test_create_with_add_only(self):
        user = self._create_user('craddonly', ['add_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_create')).status_code, 403,
        )

    def test_create_with_change_only(self):
        user = self._create_user('crchgonly', ['change_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_create')).status_code, 403,
        )

    def test_create_with_both(self):
        user = self._create_user('crboth', ['add_product', 'change_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_create')).status_code, 200,
        )

    # ── Product update (GestorRequiredMixin → add_product + change_product) ─

    def test_update_without_perms(self):
        user = self._create_user('upno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_update', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_update_with_add_only(self):
        user = self._create_user('upaddonly', ['add_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_update', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_update_with_change_only(self):
        user = self._create_user('upchgonly', ['change_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_update', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_update_with_both(self):
        user = self._create_user('upboth', ['add_product', 'change_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_update', kwargs={'pk': self.product.pk}),
            ).status_code, 200,
        )

    # ── Product delete (GestorRequiredMixin → add_product + change_product) ─

    def test_delete_without_perms(self):
        user = self._create_user('delno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_delete', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_delete_with_both(self):
        user = self._create_user('delboth', ['add_product', 'change_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('products:product_delete', kwargs={'pk': self.product.pk}),
            ).status_code, 200,
        )

    # ── Bulk delete (PermissionRequiredMixin → delete_product) ─────────

    def test_bulk_delete_without(self):
        user = self._create_user('bulkno')
        self._login(user)
        self.assertEqual(
            self.client.post(
                reverse('products:product_bulk_delete'), {'ids': []},
            ).status_code, 403,
        )

    def test_bulk_delete_with(self):
        user = self._create_user('bulkyes', ['delete_product'])
        self._login(user)
        self.assertEqual(
            self.client.post(
                reverse('products:product_bulk_delete'), {'ids': []},
            ).status_code, 302,
        )

    # ── Trash / Restore / Hard delete (delete_product) ─────────────────

    def test_trash_without(self):
        user = self._create_user('trashno')
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_trash')).status_code, 403,
        )

    def test_trash_with(self):
        user = self._create_user('trashyes', ['delete_product'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('products:product_trash')).status_code, 200,
        )

    def test_restore_without(self):
        user = self._create_user('restno')
        self._login(user)
        self.assertEqual(
            self.client.post(
                reverse('products:product_restore', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    def test_hard_delete_without(self):
        user = self._create_user('hardno')
        self._login(user)
        self.assertEqual(
            self.client.post(
                reverse('products:product_hard_delete', kwargs={'pk': self.product.pk}),
            ).status_code, 403,
        )

    # ── Inflow permissions ────────────────────────────────────────────

    def test_inflow_create_without(self):
        user = self._create_user('inflowno')
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('inflows:inflow_create')).status_code, 403,
        )

    def test_inflow_create_with_add(self):
        user = self._create_user('inflowyes', ['add_inflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('inflows:inflow_create')).status_code, 200,
        )

    def test_inflow_update_without(self):
        inflow = InflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('inflowupno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_update', kwargs={'pk': inflow.pk}),
            ).status_code, 403,
        )

    def test_inflow_update_with_change(self):
        inflow = InflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('inflowupyes', ['change_inflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_update', kwargs={'pk': inflow.pk}),
            ).status_code, 200,
        )

    def test_inflow_delete_without(self):
        inflow = InflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('inflowdelno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_delete', kwargs={'pk': inflow.pk}),
            ).status_code, 403,
        )

    def test_inflow_delete_with(self):
        inflow = InflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('inflowdelyes', ['delete_inflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('inflows:inflow_delete', kwargs={'pk': inflow.pk}),
            ).status_code, 200,
        )

    # ── Outflow permissions ───────────────────────────────────────────

    def test_outflow_create_without(self):
        user = self._create_user('outno')
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('outflows:outflow_create')).status_code, 403,
        )

    def test_outflow_create_with_add(self):
        user = self._create_user('outyes', ['add_outflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(reverse('outflows:outflow_create')).status_code, 200,
        )

    def test_outflow_update_without(self):
        outflow = OutflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('outupno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_update', kwargs={'pk': outflow.pk}),
            ).status_code, 403,
        )

    def test_outflow_update_with_change(self):
        outflow = OutflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('outupyes', ['change_outflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_update', kwargs={'pk': outflow.pk}),
            ).status_code, 200,
        )

    def test_outflow_delete_without(self):
        outflow = OutflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('outdelno')
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_delete', kwargs={'pk': outflow.pk}),
            ).status_code, 403,
        )

    def test_outflow_delete_with(self):
        outflow = OutflowFactory(product=self.product, tenant=self.tenant)
        user = self._create_user('outdelyes', ['delete_outflow'])
        self._login(user)
        self.assertEqual(
            self.client.get(
                reverse('outflows:outflow_delete', kwargs={'pk': outflow.pk}),
            ).status_code, 200,
        )
