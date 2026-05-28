import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional
from django.core.validators import URLValidator, validate_email
from django.core.exceptions import ValidationError


@dataclass
class CompanyInfo:
    name: str = ''
    location: str = ''
    email: str = ''
    phone: str = ''


@dataclass
class DatabaseConfig:
    engine: str = 'django.db.backends.sqlite3'
    name: str = 'db.sqlite3'


@dataclass
class RedisConfig:
    url: str = 'redis://127.0.0.1:6379/0'


@dataclass
class CeleryConfig:
    broker_url: str = ''
    result_backend: str = ''


@dataclass
class AppConfig:
    company: CompanyInfo = field(default_factory=CompanyInfo)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    debug: bool = False
    allowed_hosts: list = field(default_factory=list)


ALLOWED_KEYS = {'company', 'database', 'redis', 'celery', 'debug', 'allowed_hosts'}
ALLOWED_COMPANY_KEYS = {'name', 'location', 'email', 'phone'}
ALLOWED_DATABASE_KEYS = {'engine', 'name'}
ALLOWED_REDIS_KEYS = {'url'}
ALLOWED_CELERY_KEYS = {'broker_url', 'result_backend'}


def _validate_extra_keys(data: dict, allowed: set, section: str) -> None:
    extra = set(data.keys()) - allowed
    if extra:
        raise ValueError(f"Unknown config keys in '{section}': {', '.join(sorted(extra))}")


def _validate_config_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError('Config root must be a JSON object')
    _validate_extra_keys(data, ALLOWED_KEYS, 'root')

    if 'company' in data:
        _validate_extra_keys(data['company'], ALLOWED_COMPANY_KEYS, 'company')
        company = data['company']
        if company.get('email'):
            try:
                validate_email(company['email'])
            except ValidationError as e:
                raise ValueError(f"Invalid company email: {e}") from e

    if 'database' in data:
        _validate_extra_keys(data['database'], ALLOWED_DATABASE_KEYS, 'database')
        engine = data['database'].get('engine', '')
        if engine and 'django.db.backends' not in engine:
            raise ValueError(f"Invalid database engine: '{engine}'")

    if 'redis' in data:
        _validate_extra_keys(data['redis'], ALLOWED_REDIS_KEYS, 'redis')

    if 'celery' in data:
        _validate_extra_keys(data['celery'], ALLOWED_CELERY_KEYS, 'celery')

    if 'debug' in data and not isinstance(data['debug'], bool):
        raise ValueError("'debug' must be a boolean")

    if 'allowed_hosts' in data:
        if not isinstance(data['allowed_hosts'], list):
            raise ValueError("'allowed_hosts' must be a list of strings")
        for host in data['allowed_hosts']:
            if not isinstance(host, str):
                raise ValueError(f"Invalid host in allowed_hosts: {host}")


class ConfigParser:
    """Parser para ficheiros de configuração JSON com validação."""

    def parse(self, path: Path) -> AppConfig:
        data = json.loads(path.read_text(encoding='utf-8'))
        _validate_config_data(data)
        return AppConfig(
            company=CompanyInfo(**data.get('company', {})),
            database=DatabaseConfig(**data.get('database', {})),
            redis=RedisConfig(**data.get('redis', {})),
            celery=CeleryConfig(**data.get('celery', {})),
            debug=data.get('debug', False),
            allowed_hosts=data.get('allowed_hosts', []),
        )

    def parse_string(self, content: str) -> AppConfig:
        return self.parse_from_dict(json.loads(content))

    def parse_from_dict(self, data: dict) -> AppConfig:
        _validate_config_data(data)
        return AppConfig(
            company=CompanyInfo(**data.get('company', {})),
            database=DatabaseConfig(**data.get('database', {})),
            redis=RedisConfig(**data.get('redis', {})),
            celery=CeleryConfig(**data.get('celery', {})),
            debug=data.get('debug', False),
            allowed_hosts=data.get('allowed_hosts', []),
        )


class ConfigPrettyPrinter:
    def to_dict(self, config: AppConfig) -> dict:
        return {
            'company': asdict(config.company),
            'database': asdict(config.database),
            'redis': asdict(config.redis),
            'celery': asdict(config.celery),
            'debug': config.debug,
            'allowed_hosts': config.allowed_hosts,
        }

    def to_json(self, config: AppConfig, indent: int = 2) -> str:
        return json.dumps(self.to_dict(config), indent=indent, ensure_ascii=False)

    def to_file(self, config: AppConfig, path: Path) -> None:
        path.write_text(self.to_json(config), encoding='utf-8')
