from io import StringIO
from django.test import TestCase
from django.core.management import call_command


class MigrationTest(TestCase):
    def test_showmigrations_no_unapplied(self):
        out = StringIO()
        call_command('showmigrations', format='plan', stdout=out)
        output = out.getvalue()
        self.assertNotIn('[ ]', output)
