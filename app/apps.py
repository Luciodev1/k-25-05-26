import logging
from pathlib import Path
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class SgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        config_path = settings.BASE_DIR / 'config.json'
        if not config_path.exists():
            return
        try:
            from app.config_parser import ConfigParser
            config = ConfigParser().parse(config_path)
            if config.company.name:
                settings.COMPANY_INFO['NAME'] = config.company.name
            logger.info('Config carregado: %s', config.company.name or '(sem nome)')
        except Exception:
            logger.exception('Erro ao carregar config.json')
