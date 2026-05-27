import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tenants.models import Tenant, TenantUser, TenantSettings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cria uma nova empresa (tenant) e associa um utilizador como administrador.'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Nome da empresa')
        parser.add_argument('slug', type=str, help='Slug da empresa (URL amigável)')
        parser.add_argument('--username', type=str, help='Username do administrador (opcional)')
        parser.add_argument('--description', type=str, default='', help='Descrição da empresa')
        parser.add_argument('--max-users', type=int, default=10, help='Número máximo de utilizadores')

    def handle(self, *args, **options):
        from django.utils.text import slugify

        name = options['name']
        slug = options['slug']

        if slug != slugify(slug):
            self.stderr.write(self.style.ERROR('Slug inválido. Use apenas letras, números e hífen.'))
            return

        if Tenant.objects.filter(slug=slug).exists():
            self.stderr.write(self.style.ERROR(f'Já existe uma empresa com o slug "{slug}".'))
            return

        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            description=options['description'],
            max_users=options['max_users'],
        )
        TenantSettings.objects.create(tenant=tenant)
        self.stdout.write(self.style.SUCCESS(f'Empresa "{name}" criada com sucesso (ID: {tenant.id}).'))

        username = options.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                TenantUser.objects.create(
                    user=user,
                    tenant=tenant,
                    role='admin',
                    is_primary=True,
                )
                self.stdout.write(self.style.SUCCESS(f'Utilizador "{username}" associado como admin.'))
            except User.DoesNotExist:
                self.stderr.write(
                    self.style.WARNING(f'Utilizador "{username}" não encontrado. '
                                       f'Crie-o primeiro e associe manualmente.')
                )

        logger.info('Tenant criado via command: name=%s slug=%s', name, slug)
