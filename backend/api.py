from ninja import Router

from backend.views.accounts.login import router as login_router
from backend.views.accounts.logout import router as logout_router
from backend.views.accounts.profile import router as profile_router
from backend.views.accounts.recover import router as recover_router
from backend.views.accounts.signup import router as signup_router
from backend.views.actions.list_notes import router as list_notes_router
from backend.views.actions.note_selected import router as note_selected_router
from backend.views.healthcheck import router as healthcheck_router
from fAIth.api_tags import APITags

healcheck_api = Router(tags=[APITags.HEALTH])
backend_api = Router(tags=[APITags.BACKEND])

# Aggregate all backend health check endpoints
healcheck_api.add_router("", healthcheck_router)

# Aggregate all backend account endpoints
backend_api.add_router("", profile_router)
backend_api.add_router("", login_router)
backend_api.add_router("", logout_router)
backend_api.add_router("", recover_router)
backend_api.add_router("", signup_router)

# Aggregate all backend actions endpoints
backend_api.add_router("", list_notes_router)
backend_api.add_router("", note_selected_router)
