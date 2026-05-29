import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica a saúde da aplicação (base de dados, cache, versão)'

    def handle(self, *args, **options):
        errors = []

        db_ok = False
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                db_ok = cursor.fetchone() is not None
        except Exception as e:
            logger.exception('Health check DB failed')
            errors.append(f'database: {e}')

        cache_ok = None
        try:
            from django.core.cache import cache
            cache.set('__health__', 'ok', 5)
            cache_ok = cache.get('__health__') == 'ok'
        except Exception as e:
            cache_ok = False
            errors.append(f'cache: {e}')

        version = getattr(settings, 'APP_VERSION', '1.0.0')

        if errors:
            self.stdout.write(self.style.ERROR('UNHEALTHY'))
            for err in errors:
                self.stderr.write(self.style.ERROR(f'  {err}'))
            self.stdout.write(self.style.WARNING(f'  version: {version}'))
            raise CommandError('Health check failed')

        self.stdout.write(self.style.SUCCESS('HEALTHY'))
        self.stdout.write(f'  database: {db_ok}')
        self.stdout.write(f'  cache: {cache_ok}')
        self.stdout.write(f'  version: {version}')
