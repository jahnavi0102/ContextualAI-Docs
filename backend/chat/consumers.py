# backend/chat/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

import logging
logger = logging.getLogger(__name__)


User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        # Get the token from the query string
        query_string = self.scope['query_string'].decode()
        token_str = query_string.split('token=')[1] if 'token=' in query_string else None

        if not token_str:
            await self.close(code=4001) # Close if no token
            return

        try:
            # Validate the token and get the user
            access_token = AccessToken(token_str)
            user_id = access_token['user_id']
            self.user = await self.get_user_from_id(user_id)
            if self.user.is_authenticated:
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
            else:
                await self.close(code=4002) # Close if user is not authenticated
        except (ObjectDoesNotExist, Exception) as e:
            await self.close(code=4003) # Close on token validation failure

    async def disconnect(self, close_code):
        if self.user and self.user.is_authenticated:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    async def get_user_from_id(self, user_id):
        # Asynchronously get the user to avoid blocking
        try:
            return await User.objects.aget(id=user_id)
        except User.DoesNotExist:
            return None