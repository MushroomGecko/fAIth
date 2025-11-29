from django.apps import AppConfig
from django_asgi_lifespan.register import register_lifespan_manager
from ai.globals import (
    milvus_db_lifespan_manager,
    completions_lifespan_manager,
)
import logging

logger = logging.getLogger(__name__)

class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"

    def ready(self):
        """Ready the app."""
        logger.info("Registering lifecycle manager functions")
        register_lifespan_manager(context_manager=milvus_db_lifespan_manager)
        register_lifespan_manager(context_manager=completions_lifespan_manager)