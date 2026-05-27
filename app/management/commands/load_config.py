from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from app.config_parser import ConfigParser, ConfigPrettyPrinter


class Command(BaseCommand):
    help = 'Carrega e valida ficheiro de configuração JSON'

    def add_arguments(self, parser):
        parser.add_argument('config_file', type=str, help='Caminho para config.json')
        parser.add_argument('--export', type=str, help='Exportar config normalizado para ficheiro')

    def handle(self, *args, **options):
        path = Path(options['config_file'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Ficheiro não encontrado: {path}'))
            return

        try:
            parser = ConfigParser()
            config = parser.parse(path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erro ao analisar config.json: {e}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Config válido: {path.name}'))
        self.stdout.write(f"  Empresa: {config.company.name}")
        self.stdout.write(f"  Debug: {config.debug}")
        self.stdout.write(f"  Hosts: {', '.join(config.allowed_hosts)}")

        if config.company.name:
            settings.COMPANY_INFO['NAME'] = config.company.name

        if options.get('export'):
            try:
                ConfigPrettyPrinter().to_file(config, Path(options['export']))
                self.stdout.write(self.style.SUCCESS(f'Exportado para {options["export"]}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Erro ao exportar config: {e}'))
