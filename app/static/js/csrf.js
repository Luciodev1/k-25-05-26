/**
 * Utilitário CSRF para requisições AJAX (fetch, XMLHttpRequest, HTMX).
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function setupCSRF() {
    const csrftoken = getCookie('csrftoken');
    if (!csrftoken) return;

    if (typeof htmx !== 'undefined') {
        document.body.addEventListener('htmx:configRequest', function (event) {
            event.detail.headers['X-CSRFToken'] = csrftoken;
        });
    }

    const originalFetch = window.fetch;
    window.fetch = function (url, options) {
        options = options || {};
        const method = (options.method || 'GET').toUpperCase();
        if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
            options.headers = options.headers || {};
            if (!options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = csrftoken;
            }
        }
        return originalFetch(url, options);
    };
}

document.addEventListener('DOMContentLoaded', setupCSRF);
