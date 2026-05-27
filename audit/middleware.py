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


class AuditMiddleware:
    """Armazena o utilizador actual na thread local para uso nos signals."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            clear_current_user()
