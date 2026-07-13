"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path, override=True)

import os  # noqa: E402

from django.core.wsgi import get_wsgi_application  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
