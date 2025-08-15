#core\middleware.py
import logging
from django.utils import timezone

logger = logging.getLogger('gaudi')

class GaudiLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'gaudi' in request.path.lower():
            # Log dettagli richiesta
            logger.info(
                f"Operazione Gaudì - "
                f"Timestamp: {timezone.now().isoformat()}, "
                f"User: {request.user}, "
                f"IP: {request.META.get('REMOTE_ADDR')}, "
                f"Method: {request.method}, "
                f"Path: {request.path}"
            )
            
            # Log contenuti richiesta per debug se necessario
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"POST Data: {request.POST}")
                logger.debug(f"Files: {request.FILES}")

        response = self.get_response(request)

        # Log risposta per operazioni Gaudì
        if 'gaudi' in request.path.lower():
            logger.info(
                f"Risposta Gaudì - "
                f"Status: {response.status_code}, "
                f"Path: {request.path}"
            )

        return response