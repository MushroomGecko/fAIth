from adrf.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class HealthcheckView(APIView):
    def get(self, request):
        try:
            # Implicit: if we reach here, webapp is running
            # Check database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return Response({"status": "OK"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Healthcheck failed: {str(e)}")
            # Return the actual DB error
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )