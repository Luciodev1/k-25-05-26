import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ['DJANGO_DEBUG'] = 'True'
django.setup()
