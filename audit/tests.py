from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from brands.models import Brand
from categories.models import Category
from products.models import Product
from .models import AuditLog
from .templatetags.notification_tags import get_notifications, NotificationCollection, NotificationItem


class AuditLogModelTest(TestCase):
    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            action='CREATE',
            model_name='Product',
            object_id='1',
            object_repr='Test Product',
            changes={'title': {'new': 'Test Product'}},
        )
        self.assertIn('Criacao', str(log))
        self.assertIn('Product', str(log))

    def test_action_choices(self):
        self.assertEqual(len(AuditLog.ACTION_CHOICES), 3)
        actions = [c[0] for c in AuditLog.ACTION_CHOICES]
        self.assertIn('CREATE', actions)
        self.assertIn('UPDATE', actions)
        self.assertIn('DELETE', actions)


class AuditSignalTest(TestCase):
    """Testa se os signals de auditoria registam accoes correctamente."""

    def test_create_product_logged(self):
        """Criar um produto deve gerar um log de auditoria."""
        brand = Brand.objects.create(name='Brand')
        category = Category.objects.create(name='Cat')
        Product.objects.create(
            title='Test Product',
            category=category,
            brand=brand,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('15.00'),
        )
        log = AuditLog.objects.filter(model_name='Product', action='CREATE').first()
        self.assertIsNotNone(log)
        # changes pode estar vazio se o middleware nao capturou o user
        # mas o log deve existir
        self.assertEqual(log.model_name, 'Product')

    def test_delete_product_logged(self):
        """Eliminar um produto deve gerar um log de auditoria."""
        brand = Brand.objects.create(name='Brand')
        category = Category.objects.create(name='Cat')
        product = Product.objects.create(
            title='ToDelete',
            category=category,
            brand=brand,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('15.00'),
        )
        product.delete()
        log = AuditLog.objects.filter(model_name='Product', action='DELETE').first()
        self.assertIsNotNone(log)

    def test_update_product_logged(self):
        """Actualizar um produto deve gerar um log de UPDATE."""
        brand = Brand.objects.create(name='Brand')
        category = Category.objects.create(name='Cat')
        product = Product.objects.create(
            title='Original',
            category=category,
            brand=brand,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('15.00'),
        )
        AuditLog.objects.filter(action='CREATE').delete()

        product.title = 'Updated'
        product.save()

        log = AuditLog.objects.filter(model_name='Product', action='UPDATE').first()
        self.assertIsNotNone(log)

    def test_audit_log_model_str(self):
        """Verificar representacao string do log."""
        log = AuditLog.objects.create(
            action='CREATE',
            model_name='Product',
            object_id='1',
            object_repr='Test Product',
        )
        self.assertIn('Criacao', str(log))
        self.assertIn('Product', str(log))

class AuditViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'a@t.com', 'pass')
        for i in range(5):
            AuditLog.objects.create(
                action='CREATE' if i % 2 == 0 else 'UPDATE',
                model_name='Product',
                object_id=str(i),
                object_repr=f'Product {i}',
                changes={'name': {'new': f'Product {i}'}},
                user=cls.user,
            )

    def test_audit_list_requires_permission(self):
        response = self.client.get(reverse('audit:audit_list'))
        self.assertEqual(response.status_code, 403)

    def test_audit_list_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('audit:audit_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product')
        self.assertIn('logs', response.context)
        self.assertIn('action_choices', response.context)

    def test_audit_list_with_action_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('audit:audit_list'), {'action': 'CREATE'})
        self.assertEqual(response.status_code, 200)

    def test_audit_list_with_model_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('audit:audit_list'), {'model': 'Product'})
        self.assertEqual(response.status_code, 200)

    def test_activity_feed_requires_permission(self):
        response = self.client.get(reverse('audit:activity_feed'))
        self.assertEqual(response.status_code, 403)

    def test_activity_feed_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('audit:activity_feed'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_activities', response.context)
        self.assertEqual(len(response.context['recent_activities']), 5)

    def test_activity_feed_with_tenant(self):
        from tenants.models import Tenant, TenantUser
        tenant = Tenant.objects.create(name='T', slug='t')
        TenantUser.objects.create(user=self.user, tenant=tenant)
        AuditLog.objects.create(
            action='DELETE', model_name='Brand',
            object_id='99', object_repr='Other', tenant=tenant,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('audit:activity_feed'))
        self.assertEqual(response.status_code, 200)


class NotificationTagTest(TestCase):
    def test_unauthenticated_returns_empty(self):
        class MockRequest:
            user = type('u', (), {'is_authenticated': False})()
        context = {'request': MockRequest()}
        result = get_notifications(context)
        self.assertEqual(result.count, 0)

    def test_notification_item_attrs(self):
        item = NotificationItem('Title', 'Message', '/url/', 'bi-icon', 'text-danger')
        self.assertEqual(item.title, 'Title')
        self.assertEqual(item.message, 'Message')
        self.assertEqual(item.url, '/url/')

    def test_notification_collection_count(self):
        nc = NotificationCollection()
        self.assertEqual(nc.count, 0)
        nc.items = [1, 2]
        self.assertEqual(nc.count, 2)

    def test_get_notifications_low_stock(self):
        brand = Brand.objects.create(name='B')
        cat = Category.objects.create(name='C')
        Product.objects.create(
            title='LowStock', category=cat, brand=brand,
            cost_price=Decimal('10'), selling_price=Decimal('15'),
            quantity=Decimal('3'),
        )
        user = User.objects.create_superuser('admin', 'a@t.com', 'pass')

        class MockRequest:
            tenant = None
        req = MockRequest()
        req.user = user
        context = {'request': req}
        result = get_notifications(context)
        self.assertGreaterEqual(result.count, 1)
