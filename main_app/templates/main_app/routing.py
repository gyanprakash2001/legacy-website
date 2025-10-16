from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Matches /ws/chat/room_name_slug/
    re_path(r'ws/chat/(?P<room_name_slug>\w+)/$', consumers.CollegeChatConsumer.as_asgi()),
]