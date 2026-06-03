from django.shortcuts import redirect


class PortalErrorRedirectMiddleware:
    """Redireciona 403/404 no portal para a página anterior ou dashboard."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code in (403, 404) and request.path.startswith('/portal/'):
            referer = request.META.get('HTTP_REFERER', '')
            if referer and '/portal/' in referer:
                return redirect(referer)
            return redirect('portal:dashboard')

        return response
