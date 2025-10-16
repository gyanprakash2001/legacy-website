import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync


class CollegeChatConsumer(WebsocketConsumer):

    def connect(self):
        # 1. Extract the room name (the sanitized college name slug) from the URL path
        # The URL we set up is /ws/chat/<room_name_slug>/
        self.room_name = self.scope['url_route']['kwargs']['room_name_slug']
        # 2. Create the Channel Group name (e.g., 'chat_kristu_jayanti')
        self.room_group_name = 'chat_%s' % self.room_name

        # 3. Join the room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        # 4. Accept the WebSocket connection
        self.accept()

        # Optional: Send a confirmation message upon connection
        self.send(text_data=json.dumps({
            'message': f"Connected to {self.room_name.replace('_', ' ').title()} Chat.",
            'sender': 'System'
        }))

    def disconnect(self, close_code):
        # Leave room group on disconnect
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Check for simple text messages (the initial logic)
        if text_data_json.get('type') == 'text_only':
            message = text_data_json['message']
            sender = text_data_json['sender']

            # Send message to room group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'text',  # IMPORTANT: Specify message type
                    'content': message,
                    'sender': sender
                    # Note: Full data (like ID, URLs) is NOT needed for simple text.
                    # This relies on the frontend sending simplified data.
                }
            )

        # CRITICAL: For media, the signal comes from the Django view, not directly from the browser's JS receive.
        # The frontend JS will call the AJAX view, and the AJAX view will call group_send.

    # Receive message from room group (MODIFIED to handle richer data)
    def chat_message(self, event):
        # This method receives a full payload, whether it's simple text or media

        # Prepare the data dictionary to send to the WebSocket
        send_data = {
            'message_type': event.get('message_type', 'text'),
            'sender': event['sender'],
            'content': event.get('content'),

            # Media/Upload specific fields:
            'message_id': event.get('message_id'),
            'media_url': event.get('media_url'),
            'timestamp_str': event.get('timestamp_str'),
            'profile_icon_url': event.get('profile_icon_url'),
        }

        # Send message to WebSocket (sends data back to the browser)
        self.send(text_data=json.dumps(send_data))

    def chat_delete(self, event):
        message_id = event['message_id']

        # Send deletion instruction to WebSocket (sends data back to the browser)
        self.send(text_data=json.dumps({
            'type': 'delete_instruction',  # Instructs the frontend JS what to do
            'message_id': message_id
        }))