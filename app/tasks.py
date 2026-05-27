import logging
import shutil
from datetime import datetime
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def backup_database(self):
    """Backup diário da base de dados SQLite com rotação."""
    db_path = Path(settings.DATABASES['default']['NAME'])
    if not db_path.exists():
        logger.error('Base de dados não encontrada: %s', db_path)
        return {'status': 'error', 'message': 'Database not found'}

    backup_dir = Path(getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups'))
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'db_backup_{timestamp}.sqlite3'

    try:
        shutil.copy2(db_path, backup_path)
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info('Backup criado: %s (%.2f MB)', backup_path, size_mb)

        backups = sorted(backup_dir.glob('db_backup_*.sqlite3'), reverse=True)
        for old in backups[10:]:
            old.unlink()
            logger.info('Backup antigo removido: %s', old)

        return {'status': 'ok', 'path': str(backup_path), 'size_mb': round(size_mb, 2)}
    except (IOError, OSError) as exc:
        logger.exception('Erro no backup da base de dados')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def notify_task_completion(user_email, task_name, result_path=None):
    """Notifica por email a conclusão de uma tarefa assíncrona."""
    if not user_email:
        return
    body = f'A tarefa "{task_name}" foi concluída com sucesso.'
    if result_path:
        body += f'\n\nFicheiro: {result_path}'
    try:
        send_mail(
            subject=f'[SGE] Tarefa concluída: {task_name}',
            message=body,
            from_email=None,
            recipient_list=[user_email],
            fail_silently=True,
        )
    except Exception:
        # smtplib.SMTPException ou outras falhas de email não devem
        # interromper o fluxo principal.
        logger.exception('Falha ao enviar email de notificação')
