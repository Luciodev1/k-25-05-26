from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from customers.models import Customer
from portal.models import CustomerAccess


class Command(BaseCommand):
    help = 'Cria acesso ao portal do cliente para um cliente existente'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente')
        parser.add_argument('username', type=str, help='Nome de utilizador para o login')
        parser.add_argument('password', type=str, help='Palavra-passe para o login')
        parser.add_argument('--email', type=str, default='', help='Email do utilizador (opcional)')

    def handle(self, *args, **options):
        try:
            customer = Customer.objects.get(pk=options['customer_id'])
        except Customer.DoesNotExist:
            raise CommandError(f'Cliente com ID {options["customer_id"]} não encontrado.')

        if User.objects.filter(username=options['username']).exists():
            raise CommandError(f'Utilizador "{options["username"]}" já existe.')

        user = User.objects.create_user(
            username=options['username'],
            email=options['email'],
            password=options['password'],
        )

        access = CustomerAccess.objects.create(
            user=user,
            customer=customer,
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Acesso criado para {customer.name} (user: {user.username})'
        ))
