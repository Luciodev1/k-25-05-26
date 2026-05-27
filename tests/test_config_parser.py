import json
import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from app.config_parser import ConfigParser, ConfigPrettyPrinter, AppConfig, CompanyInfo


class ConfigParserTest(SimpleTestCase):
    def test_round_trip(self):
        data = {
            'company': {'name': 'Test Co', 'location': 'Luanda', 'email': 'a@b.co', 'phone': '123'},
            'debug': True,
            'allowed_hosts': ['localhost'],
        }
        parser = ConfigParser()
        config = parser.parse_from_dict(data)
        printer = ConfigPrettyPrinter()
        restored = parser.parse_from_dict(json.loads(printer.to_json(config)))
        self.assertEqual(restored.company.name, 'Test Co')
        self.assertTrue(restored.debug)

    def test_parse_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({'company': {'name': 'K'}}, f)
            path = Path(f.name)
        config = ConfigParser().parse(path)
        self.assertEqual(config.company.name, 'K')
        path.unlink()

    def test_invalid_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            ConfigParser().parse_string('{invalid')
