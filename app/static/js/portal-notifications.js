(() => {
    'use strict';

    const NOTIFICATION_SOUND = false;
    let ws = null;
    let reconnectTimer = null;
    let notificationCount = 0;

    function getNotificationBadge() {
        return document.getElementById('notification-badge');
    }

    function getNotificationDropdown() {
        return document.getElementById('notification-list');
    }

    function getNotificationIcon() {
        return document.getElementById('notification-bell-icon');
    }

    function updateBadge(count) {
        const badge = getNotificationBadge();
        if (!badge) return;
        notificationCount = count;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    }

    function addNotificationToDropdown(title, message, url, icon, color) {
        const dropdown = getNotificationDropdown();
        if (!dropdown) return;

        const item = document.createElement('a');
        if (url) {
            item.href = url;
            item.className = 'dropdown-item notification-item py-2 px-3';
        } else {
            item.className = 'dropdown-item notification-item py-2 px-3 text-decoration-none';
            item.style.cursor = 'default';
        }
        item.style.borderRadius = '8px';

        item.innerHTML = `
            <div class="d-flex align-items-start gap-2">
                <i class="bi ${icon || 'bi-info-circle'} ${color || 'text-primary'} fs-5 mt-1 flex-shrink-0"></i>
                <div class="small">
                    <div class="fw-semibold mb-1">${title}</div>
                    <div class="text-muted" style="font-size:0.75rem;">${message}</div>
                </div>
            </div>
        `;
        dropdown.insertBefore(item, dropdown.firstChild);

        const clearAll = dropdown.querySelector('.notification-clear-all');
        if (clearAll) {
            dropdown.insertBefore(item, clearAll);
        }

        const count = dropdown.querySelectorAll('.notification-item').length;
        updateBadge(count);

        if (count > 20) {
            const lastItem = dropdown.querySelectorAll('.notification-item')[count - 1];
            if (lastItem && lastItem !== clearAll) lastItem.remove();
        }
    }

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;

        if (ws && ws.readyState === WebSocket.OPEN) return;

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = function () {
                console.log('[Portal WS] Conectado');
                if (reconnectTimer) {
                    clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
            };

            ws.onmessage = function (event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.action === 'notification') {
                        addNotificationToDropdown(
                            data.title || 'Notificação',
                            data.message || '',
                            data.url || '',
                            data.icon || 'bi-info-circle',
                            data.color || 'text-primary'
                        );
                    } else if (data.action === 'pong') {
                        // keep-alive response
                    }
                } catch (e) {
                    console.warn('[Portal WS] Erro ao processar mensagem:', e);
                }
            };

            ws.onclose = function () {
                console.log('[Portal WS] Desconectado, a reconectar em 5s...');
                ws = null;
                reconnectTimer = setTimeout(connectWebSocket, 5000);
            };

            ws.onerror = function () {
                console.warn('[Portal WS] Erro de conexão');
                ws && ws.close();
            };
        } catch (e) {
            console.warn('[Portal WS] Falha ao conectar:', e);
            reconnectTimer = setTimeout(connectWebSocket, 10000);
        }
    }

    function sendPing() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping' }));
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const bell = document.getElementById('notification-bell');
        if (bell) {
            connectWebSocket();
            setInterval(sendPing, 30000);
        }
    });
})();
