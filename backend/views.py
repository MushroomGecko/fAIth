import logging
import json

from django.db import connection
from django.http import HttpResponse
from asgiref.sync import sync_to_async
from ninja import Router
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

router = Router()


@sync_to_async
def check_db():
    """Verify database connectivity."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


@router.get("/healthcheck", tags=[APITags.HEALTH])
async def healthcheck(request):
    """
    API endpoint for health checks and system status.

    Verifies that the application and database are functioning correctly.
    Used by load balancers, monitoring systems, and deployment orchestration.
    
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
        await check_db()
        
        # 200 - OK
        return HttpResponse(
            json.dumps({"status": "OK"}),
            status=200,
            content_type="application/json"
        )
    except Exception as e:
        logger.error(f"Healthcheck failed: {str(e)}")
        # Return actual error details for debugging
        # 503 - Service Unavailable
        return HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status=503,
            content_type="application/json"
        )