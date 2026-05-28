import logging
import threading

logger = logging.getLogger(__name__)
_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    _thread_locals.user = user


def clear_current_user():
    if hasattr(_thread_locals, 'user'):
        del _thread_locals.user


def get_current_request():
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    _thread_locals.request = request


def clear_current_request():
    if hasattr(_thread_locals, 'request'):
        del _thread_locals.request


class AuditMiddleware:
    """Armazena o utilizador actual na thread local para uso nos signals."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, 'user', None))
        set_current_request(request)
        try:
            return self.get_response(request)
        finally:
            clear_current_user()
            clear_current_request()
