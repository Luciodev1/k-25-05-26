import factory
from django.contrib.auth.models import User
from decimal import Decimal


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'tenants.Tenant'
        django_get_or_create = ('slug',)

    name = factory.Sequence(lambda n: f'Tenant {n}')
    slug = factory.Sequence(lambda n: f'tenant-{n}')
    is_active = True


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'brands.Brand'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Marca {n}')


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'categories.Category'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Categoria {n}')


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'suppliers.Supplier'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Fornecedor {n}')
    nif = factory.Sequence(lambda n: f'{n:09d}')
    email = factory.Sequence(lambda n: f'fornecedor{n}@example.com')


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'customers.Customer'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Cliente {n}')
    nif = factory.Sequence(lambda n: f'{900000000 + n:09d}')
    email = factory.Sequence(lambda n: f'cliente{n}@example.com')


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'products.Product'

    tenant = factory.SubFactory(TenantFactory)
    title = factory.Sequence(lambda n: f'Produto {n}')
    category = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
    cost_price = Decimal('10.00')
    selling_price = Decimal('15.00')
    quantity = Decimal('100')
    serial_number = factory.Sequence(lambda n: f'SN-{n:05d}')


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'drivers.Driver'

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f'Motorista {n}')
    phone = factory.Sequence(lambda n: f'+244 9{n:02d} 000 000')
    truck_plate = factory.Sequence(lambda n: f'LD-{n:02d}-AA-00')
    cistern_plate = factory.Sequence(lambda n: f'LD-{n:02d}-BB-00')


class InflowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'inflows.Inflow'

    tenant = factory.SubFactory(TenantFactory)
    product = factory.SubFactory(ProductFactory)
    supplier = factory.SubFactory(SupplierFactory)
    quantity = Decimal('50')
    price = Decimal('12.00')


class OutflowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'outflows.Outflow'

    tenant = factory.SubFactory(TenantFactory)
    product = factory.SubFactory(ProductFactory)
    customer = factory.SubFactory(CustomerFactory)
    quantity = Decimal('10')
    price = Decimal('15.00')


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'payments.Payment'

    tenant = factory.SubFactory(TenantFactory)
    type = 'RECEIPT'
    customer = factory.SubFactory(CustomerFactory)
    amount = Decimal('100.00')
    payment_method = 'CASH'
    date = factory.Faker('date_this_month')


class DeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'outflows.Delivery'

    tenant = factory.SubFactory(TenantFactory)
    outflow = factory.SubFactory(OutflowFactory)
    quantity = Decimal('10')
    driver = factory.SubFactory(DriverFactory)
    description = factory.Sequence(lambda n: f'Entrega #{n}')
