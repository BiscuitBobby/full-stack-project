# pcb_project/asgi.py

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pcb_project.settings')

# This is the application entry point for ASGI-compatible web servers.
application = get_asgi_application()