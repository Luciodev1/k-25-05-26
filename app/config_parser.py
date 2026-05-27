import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional


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


class ConfigParser:
    """Parser para ficheiros de configuração JSON."""

    def parse(self, path: Path) -> AppConfig:
        data = json.loads(path.read_text(encoding='utf-8'))
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
