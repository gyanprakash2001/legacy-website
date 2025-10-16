from django.urls import re_path

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# NOTE: We haven't created the consumer yet, but we will reference it.
# We will create the consumer in Step 3 inside the 'main_app' directory.
from main_app import consumers

websocket_urlpatterns = [
    # This URL pattern captures the college name (e.g., 'symbiosis-institute-of-management-studies-maharashtra')
    re_path(r'ws/community/chat/(?P<college_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    # (http->django views is added by default)

    # WebSocket handle: Sends the request to the URLRouter for processing
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})