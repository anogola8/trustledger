class SecurityHeadersMiddleware:
    """Adds a Content-Security-Policy and other defensive headers."""

    CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
           "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; "
           "font-src 'self' https://cdn.jsdelivr.net; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Content-Security-Policy', self.CSP)
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.setdefault('Referrer-Policy', 'same-origin')
        return response
