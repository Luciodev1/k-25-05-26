// WebSocket — Real-time notifications
(function () {
  let ws = null;
  let reconnectTimer = null;
  const RECONNECT_DELAY = 5000;

  function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;

    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
      console.log('[WS] Conectado');
      document.body.classList.remove('ws-disconnected');
      document.body.classList.add('ws-connected');
    };

    ws.onmessage = function (e) {
      try {
        const data = JSON.parse(e.data);
        if (data.action === 'notification') {
          showNotification(data);
        }
      } catch (err) {
        console.warn('[WS] Erro ao processar mensagem:', err);
      }
    };

    ws.onclose = function () {
      console.log('[WS] Desconectado, reconectando...');
      document.body.classList.remove('ws-connected');
      document.body.classList.add('ws-disconnected');
      scheduleReconnect();
    };

    ws.onerror = function () {
      console.warn('[WS] Erro de conexão');
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectWebSocket, RECONNECT_DELAY);
  }

  function showNotification(data) {
    // Update the notification badge
    const badge = document.querySelector('.notification-badge');
    if (badge) {
      const count = parseInt(badge.textContent || '0', 10);
      badge.textContent = count + 1;
      badge.classList.remove('d-none');
    }

    // Prepend to notification list
    const list = document.querySelector('.notification-list');
    if (list) {
      const empty = list.querySelector('.notification-empty');
      if (empty) empty.remove();

      const item = document.createElement('a');
      item.href = data.url || '#';
      item.className = 'list-group-item list-group-item-action p-3 border-0';
      item.innerHTML =
        '<div class="d-flex gap-3">' +
        '<div class="bg-body-secondary p-2 rounded-3 d-flex align-items-center justify-content-center ' +
        (data.color || 'text-primary') +
        '" style="width: 40px; height: 40px;">' +
        '<i class="bi ' + (data.icon || 'bi-info-circle') + '"></i></div>' +
        '<div class="flex-grow-1">' +
        '<div class="fw-bold small text-body">' + escapeHtml(data.title) + '</div>' +
        '<div class="extra-small text-muted">' + escapeHtml(data.message) + '</div>' +
        '</div></div>';
      list.prepend(item);
    }

    // Browser notification if permitted
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(data.title, { body: data.message, icon: '/static/favicon.ico' });
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  // Request notification permission
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }

  // Connect on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
  } else {
    connectWebSocket();
  }
})();
