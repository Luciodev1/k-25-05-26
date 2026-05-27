from decimal import Decimal
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.conf import settings

from app.tasks import backup_database, notify_task_completion


class BackupDatabaseTaskTest(TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.tmp_dir / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_backup_database_no_db(self):
        with patch('app.tasks.Path.exists', return_value=False):
            result = backup_database()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Database not found')

    def test_backup_database_success(self):
        db_path = self.backup_dir / 'live_db.sqlite3'
        db_path.write_text('valid sqlite content')
        with (
            patch('app.tasks.settings.BACKUP_DIR', str(self.backup_dir)),
            patch('app.tasks.settings.DATABASES', {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': str(db_path),
                }
            }),
        ):
            result = backup_database()
        self.assertEqual(result['status'], 'ok')
        self.assertIn('path', result)
        self.assertGreaterEqual(result['size_mb'], 0)


class NotifyTaskCompletionTaskTest(TestCase):
    @patch('app.tasks.send_mail')
    def test_notify_without_email(self, mock_send_mail):
        notify_task_completion(None, 'test_task')
        mock_send_mail.assert_not_called()

    @patch('app.tasks.send_mail')
    def test_notify_with_email(self, mock_send_mail):
        notify_task_completion('user@test.com', 'Export Report', '/tmp/report.pdf')
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]
        self.assertIn('user@test.com', call_kwargs['recipient_list'])
        self.assertIn('Export Report', call_kwargs['subject'])
        self.assertIn('/tmp/report.pdf', call_kwargs['message'])

    @patch('app.tasks.send_mail', side_effect=Exception('SMTP error'))
    def test_notify_email_failure_does_not_raise(self, mock_send_mail):
        notify_task_completion('user@test.com', 'test_task')
