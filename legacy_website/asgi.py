# legacy_website/asgi.py

import os
import sys
from pathlib import Path

# --- Configuration Setup ---

# 1. Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legacy_website.settings')

# 2. Add the project's root directory to the path.
# This assumes the directory containing both 'legacy_website' and 'main_app'
# is one level above the current file.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))


# 3. Initialize Django's ASGI application (This MUST happen before app-specific imports)
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()


# --- Channels Imports and Routing ---

# 4. Imports after Django initialization and path setup
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# This import should now work as Django's environment is loaded.
# If it fails again, the 'main_app' directory is in the wrong place or the BASE_DIR is wrong.
import main_app.routing

# 5. Define the final application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            main_app.routing.websocket_urlpatterns
        )
    ),
})