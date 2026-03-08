import logging

from adrf.views import APIView
from django.db import connection
from rest_framework import status
from rest_framework.response import Response

# Set up logging
logger = logging.getLogger(__name__)


class HealthcheckView(APIView):
    """
    API endpoint for health checks and system status.

    Verifies that the application and database are functioning correctly.
    Used by load balancers, monitoring systems, and deployment orchestration.
    """

    def get(self, request):
        """
        Check application and database health.

        Attempts to establish a database connection and execute a simple query.
        If successful, returns 200 OK. If any error occurs, returns 503 Service Unavailable.

        Parameters:
            request: The HTTP request object.

        Returns:
            Response: JSON response with status and optional error message.
                - 200 OK: {"status": "OK"} - All systems operational
                - 503 Service Unavailable: {"status": "error", "message": "<error>"} - Database or app issue
        """
        try:
            # Application is running if we reach this point (implicit check)
            # Explicitly verify database connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return Response({"status": "OK"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Healthcheck failed: {str(e)}")
            # Return actual error details for debugging
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )