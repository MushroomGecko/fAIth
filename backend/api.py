from ninja import Router

from backend.views.healthcheck import router as healthcheck_router
from fAIth.api_tags import APITags

# Aggregate all backend health check endpoints
healcheck_api = Router(tags=[APITags.HEALTH])
healcheck_api.add_router("", healthcheck_router)

# Aggregate all other backend endpoints
backend_api = Router(tags=[APITags.BACKEND])
