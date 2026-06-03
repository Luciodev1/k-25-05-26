import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user', AnonymousUser())
        url_route = self.scope.get('url_route', {})
        self.tenant_id = url_route.get('kwargs', {}).get('tenant_id')
        self.group_name = None

        if self.user.is_authenticated:
            if self.tenant_id:
                self.group_name = f'notifications_tenant_{self.tenant_id}'
            else:
                self.group_name = f'notifications_user_{self.user.id}'

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info('WebSocket connected: user=%s group=%s', self.user, self.group_name)
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info('WebSocket disconnected: group=%s', self.group_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            if action == 'ping':
                await self.send(text_data=json.dumps({'action': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def send_notification(self, event):
        """Send a notification to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'action': 'notification',
            'title': event.get('title', ''),
            'message': event.get('message', ''),
            'url': event.get('url', ''),
            'icon': event.get('icon', 'bi-info-circle'),
            'color': event.get('color', 'text-primary'),
        }))

    async def notification_update(self, event):
        """Alias for send_notification."""
        await self.send_notification(event)
