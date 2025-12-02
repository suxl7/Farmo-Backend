from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('django.security')


class SecurityLoggingMiddleware(MiddlewareMixin):
    """Middleware to log security-related requests and responses"""
    
    def process_request(self, request):
        """Log all state-changing requests with client IP"""
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            logger.info(f'{request.method} {request.path} from {self.get_client_ip(request)}')
        return None

    def process_response(self, request, response):
        """Log all error responses (4xx and 5xx)"""
        if response.status_code >= 400:
            logger.warning(f'{request.method} {request.path} - Status: {response.status_code}')
        return response

    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
