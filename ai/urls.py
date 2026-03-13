from ninja import Router
from ai.views import router as views_router

router = Router()

router.add_router("", views_router)