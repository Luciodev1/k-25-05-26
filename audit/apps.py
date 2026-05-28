from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'Auditoria'

    def ready(self):
        from audit.signals import _connect_signals
        try:
            _connect_signals()
            logger.info('Audit signals connected.')
        except Exception as exc:
            logger.warning('Could not connect audit signals: %s', exc)
