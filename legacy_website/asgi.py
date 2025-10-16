import os
import sys
from pathlib import Path

# --- CRITICAL FIX: Set Django Settings and Path First ---

# 1. Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacy_website.settings')

# 2. Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# 3. Add the project root to the system path so Python can find 'main_app'
sys.path.append(str(BASE_DIR))

# --- Now proceed with necessary imports and application loading ---

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# CRITICAL FIX 4: Use a contextually safe import after modifying sys.path
# We will keep the original import as it is the standard and should now work.
# If it fails again, try adding the app folder specifically: sys.path.append(str(BASE_DIR / 'main_app'))
import main_app.routing

# Get the Django ASGI application (This initializes Django)
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            main_app.routing.websocket_urlpatterns
        )
    ),
})