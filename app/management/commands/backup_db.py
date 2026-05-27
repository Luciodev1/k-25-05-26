import shutil
import logging
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cria um backup da base de dados SQLite'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=str(settings.BASE_DIR / 'backups'),
            help='Diretorio para guardar os backups (default: backups/)',
        )

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f'Base de dados nao encontrada: {db_path}'))
            return

        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'db_backup_{timestamp}.sqlite3'
        backup_path = output_dir / backup_name

        try:
            shutil.copy2(db_path, backup_path)
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            msg = f'Backup criado: {backup_path} ({size_mb:.2f} MB)'
            self.stdout.write(self.style.SUCCESS(msg))
            logger.info(msg)

            # Limpar backups antigos (manter ultimos 10)
            backups = sorted(output_dir.glob('db_backup_*.sqlite3'), reverse=True)
            for old_backup in backups[10:]:
                old_backup.unlink()
                logger.info(f'Backup antigo removido: {old_backup}')

        except (IOError, OSError, shutil.Error) as e:
            msg = f'Erro ao criar backup: {e}'
            self.stderr.write(self.style.ERROR(msg))
            logger.error(msg)
