import secrets


class ContentSecurityPolicyMiddleware:
    """Adiciona o header Content-Security-Policy com nonce para scripts inline."""

    SCRIPT_SRC_CDN = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js "
        "https://unpkg.com/htmx.org@2.0.4 "
        "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"
    )

    STYLE_SRC_CDN = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css "
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css "
        "https://fonts.googleapis.com"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)
        ctype = response.get('Content-Type', '')
        if not ctype.startswith('text/html'):
            return response
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' {self.SCRIPT_SRC_CDN}; "
            f"style-src 'self' 'unsafe-inline' {self.STYLE_SRC_CDN}; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        )
        return response
