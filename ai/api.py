from ninja import Router

from ai.views.general_question import router as general_question_router
from fAIth.api_tags import APITags

# Aggregate all AI endpoints
ai_api = Router(tags=[APITags.AI])
ai_api.add_router("", general_question_router)
