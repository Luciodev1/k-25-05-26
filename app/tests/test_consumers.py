import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, AnonymousUser
from app.consumers import NotificationConsumer
from unittest.mock import patch


class NotificationConsumerTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user('wstest', 'ws@t.com', 'pass')

    async def _connect(self, authenticated=True):
        communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), '/ws/notifications/')
        if authenticated:
            communicator.scope['user'] = await database_sync_to_async(
                lambda: User.objects.get(username='wstest')
            )()
        else:
            communicator.scope['user'] = AnonymousUser()
        return communicator

    async def test_connect_authenticated(self):
        communicator = await self._connect(authenticated=True)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_connect_unauthenticated(self):
        communicator = await self._connect(authenticated=False)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_receive_ping(self):
        communicator = await self._connect(authenticated=True)
        await communicator.connect()
        await communicator.send_json_to({'action': 'ping'})
        response = await communicator.receive_json_from(timeout=2)
        self.assertEqual(response['action'], 'pong')
        await communicator.disconnect()

    async def test_send_notification(self):
        from channels.layers import get_channel_layer
        communicator = await self._connect(authenticated=True)
        await communicator.connect()
        channel_layer = await database_sync_to_async(get_channel_layer)()
        await channel_layer.group_send(
            f'notifications_user_{self.user.id}',
            {
                'type': 'send_notification',
                'title': 'Test',
                'message': 'Hello',
                'url': '/portal/',
                'icon': 'bi-info',
                'color': 'text-primary',
            },
        )
        response = await communicator.receive_json_from(timeout=2)
        self.assertEqual(response['action'], 'notification')
        self.assertEqual(response['title'], 'Test')
        self.assertEqual(response['message'], 'Hello')
        await communicator.disconnect()


class PWAManifestTest(TestCase):
    def test_manifest_returns_json(self):
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        data = json.loads(response.content)
        self.assertIn('name', data)
        self.assertIn('short_name', data)
        self.assertIn('icons', data)
        self.assertEqual(data['display'], 'standalone')
        self.assertEqual(data['theme_color'], '#059669')

    def test_offline_page_renders(self):
        response = self.client.get('/offline/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sem Conexão')


class WebSocketNotificationUtilityTest(TestCase):
    @patch('app.notifications.get_channel_layer')
    def test_notify_user(self, mock_get_layer):
        from app.notifications import notify_user
        mock_layer = mock_get_layer.return_value

        notify_user(1, 'Title', 'Message', '/url/', 'bi-icon', 'text-danger')

        mock_layer.group_send.assert_called_once()
        args, _ = mock_layer.group_send.call_args
        self.assertEqual(args[0], 'notifications_user_1')
        self.assertEqual(args[1]['title'], 'Title')
        self.assertEqual(args[1]['message'], 'Message')

    @patch('app.notifications.get_channel_layer')
    def test_notify_tenant(self, mock_get_layer):
        from app.notifications import notify_tenant
        mock_layer = mock_get_layer.return_value

        notify_tenant('tenant-uuid', 'Alert', 'Something happened')

        mock_layer.group_send.assert_called_once()
        args, _ = mock_layer.group_send.call_args
        self.assertEqual(args[0], 'notifications_tenant_tenant-uuid')
        self.assertEqual(args[1]['type'], 'send_notification')
