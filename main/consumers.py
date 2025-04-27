import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async

from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json["message"]

        # 메시지 저장
        receiver = await self.get_receiver()
        if receiver:
            Message.objects.create(
                sender=self.scope['user'],
                receiver=receiver,
                content=message_content,
                is_read=False
            )
        
        async def get_receiver(self):
            try:
                receiver = await sync_to_async(User.objects.get)(username=self.room_name)
                return receiver
            except User.DoesNotExist:
                return None

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message_content}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))