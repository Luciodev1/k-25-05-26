import re
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

email_validator = EmailValidator(message='Introduza um endereço de email válido.')

ANGOLAN_NIF_PATTERN = re.compile(r'^\d{9}$')

FILE_MAGIC_BYTES = {
    'pdf': [b'%PDF'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG\r\n\x1a\n'],
}

ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}


def validate_angolan_nif(value):
    """Valida NIF angolano: exactamente 9 dígitos."""
    if not value:
        raise ValidationError('O NIF não pode estar em branco.')
    if not ANGOLAN_NIF_PATTERN.match(str(value).strip()):
        raise ValidationError('O NIF deve ter exactamente 9 dígitos numéricos.')


def validate_file_content(file_obj):
    """Valida o conteúdo do ficheiro pelos magic bytes."""
    if not file_obj:
        return
    ext = ''
    if hasattr(file_obj, 'name') and file_obj.name:
        ext = file_obj.name.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError('Tipo de ficheiro não permitido. Use PDF, JPG ou PNG.')
    header = file_obj.read(8)
    file_obj.seek(0)
    signatures = FILE_MAGIC_BYTES.get(ext, [])
    if not any(header.startswith(sig) for sig in signatures):
        raise ValidationError('O conteúdo do ficheiro não corresponde à extensão indicada.')


def validate_payment_date(value):
    """Datas de pagamento não podem estar no futuro."""
    if value and value > timezone.localdate():
        raise ValidationError('A data de pagamento não pode ser no futuro.')
