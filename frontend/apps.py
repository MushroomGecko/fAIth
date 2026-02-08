from django.apps import AppConfig
import sys
import logging

logger = logging.getLogger(__name__)

class FrontendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "frontend"

    def ready(self):
        """Ready the frontend app."""
        # Initialize the globals if not running under pytest
        if 'pytest' in sys.modules or any('pytest' in arg for arg in sys.argv):
            logger.info("Running under pytest, skipping frontend globals initialization.")
        else:
            from frontend import globals as globals_module
            globals_module.set_bible_data_root()
            globals_module.set_version_selection()
            globals_module.set_default_version()
            globals_module.set_in_order_books()
            globals_module.set_default_book()
            globals_module.set_chapter_selection()
            globals_module.set_default_chapter()
            globals_module.set_all_verses()
            globals_module.check_globals()
            logger.info("Frontend globals initialized.")