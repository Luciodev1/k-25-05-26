from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse
from app.middleware import ContentSecurityPolicyMiddleware


class ContentSecurityPolicyMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda req: HttpResponse('ok')
        self.middleware = ContentSecurityPolicyMiddleware(self.get_response)

    def test_csp_header_present(self):
        request = self.factory.get('/')
        response = self.middleware(request)
        self.assertIn('Content-Security-Policy', response)
        csp = response['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        self.assertIn("style-src 'self' 'unsafe-inline'", csp)
        self.assertIn("font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net", csp)
        self.assertIn("connect-src 'self' https://cdn.jsdelivr.net https://unpkg.com", csp)

    def test_csp_nonce_set_on_request(self):
        request = self.factory.get('/')
        self.middleware(request)
        self.assertTrue(hasattr(request, 'csp_nonce'))
        self.assertTrue(len(request.csp_nonce) > 0)

    def test_csp_contains_nonce(self):
        request = self.factory.get('/')
        response = self.middleware(request)
        csp = response['Content-Security-Policy']
        self.assertIn(f"'nonce-{request.csp_nonce}'", csp)

    def test_csp_blocks_frame_ancestors(self):
        request = self.factory.get('/')
        response = self.middleware(request)
        self.assertIn("frame-ancestors 'none'", response['Content-Security-Policy'])

    def test_csp_restricts_form_action(self):
        request = self.factory.get('/')
        response = self.middleware(request)
        self.assertIn("form-action 'self'", response['Content-Security-Policy'])


@override_settings(RATELIMIT_ENABLE=False)
class RateLimitLoginTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User
        cls.user = User.objects.create_user('testuser', 'test@test.com', 'testpass123')

    def test_login_page_accessible(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post('/accounts/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.assertIn('sessionid', self.client.cookies)

    def test_login_failure(self):
        response = self.client.post('/accounts/login/', {
            'username': 'testuser', 'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('sessionid', self.client.cookies)


@override_settings(RATELIMIT_ENABLE=True, RATELIMIT_USE_CACHE='default')
class RateLimitEnforcementTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_rate_limit_blocks_after_attempts(self):
        for _ in range(6):
            self.client.post('/accounts/login/', {
                'username': 'nonexistent', 'password': 'wrong',
            })
        response = self.client.post('/accounts/login/', {
            'username': 'nonexistent', 'password': 'wrong',
        })
        self.assertIn(response.status_code, (429, 403))
