from datetime import timedelta
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from app.validators import (
    validate_angolan_nif,
    validate_file_content,
    validate_payment_date,
    email_validator,
)


class ValidatorsTest(SimpleTestCase):
    def test_angolan_nif_valid(self):
        validate_angolan_nif('123456789')

    def test_angolan_nif_invalid(self):
        with self.assertRaises(ValidationError):
            validate_angolan_nif('12345')
        with self.assertRaises(ValidationError):
            validate_angolan_nif('abcdefghi')

    def test_payment_date_future(self):
        future = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            validate_payment_date(future)

    def test_payment_date_today_ok(self):
        validate_payment_date(timezone.localdate())

    def test_email_validator(self):
        email_validator('test@example.com')
        with self.assertRaises(ValidationError):
            email_validator('not-an-email')

    def test_file_content_pdf(self):
        f = SimpleUploadedFile('doc.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        validate_file_content(f)

    def test_file_content_invalid(self):
        f = SimpleUploadedFile('bad.pdf', b'NOTPDF', content_type='application/pdf')
        with self.assertRaises(ValidationError):
            validate_file_content(f)
