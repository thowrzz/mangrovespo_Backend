import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env before Django initializes
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

