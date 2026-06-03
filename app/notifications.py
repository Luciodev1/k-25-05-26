import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def notify_user(user_id, title, message, url='', icon='bi-info-circle', color='text-primary'):
    """Send a real-time notification to a specific user via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_user_{user_id}',
            {
                'type': 'send_notification',
                'title': title,
                'message': message,
                'url': url,
                'icon': icon,
                'color': color,
            },
        )
    except Exception as e:
        logger.warning('Failed to send WebSocket notification to user %s: %s', user_id, e)


def notify_tenant(tenant_id, title, message, url='', icon='bi-info-circle', color='text-primary'):
    """Send a real-time notification to all users in a tenant via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_tenant_{tenant_id}',
            {
                'type': 'send_notification',
                'title': title,
                'message': message,
                'url': url,
                'icon': icon,
                'color': color,
            },
        )
    except Exception as e:
        logger.warning('Failed to send WebSocket notification to tenant %s: %s', tenant_id, e)
