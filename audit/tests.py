from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from brands.models import Brand
from categories.models import Category
from products.models import Product
from .models import AuditLog


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
