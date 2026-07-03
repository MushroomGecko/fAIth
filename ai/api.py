from ninja import Router

from ai.views.general_question import router as general_question_router
from ai.views.ask_selected import router as ask_selected_router
from ai.views.summarize_chapter import router as summarize_chapter_router
from ai.views.image_search import router as image_search_router
from fAIth.api_tags import APITags

# Aggregate all AI endpoints
ai_api = Router(tags=[APITags.AI])
ai_api.add_router("", general_question_router)
ai_api.add_router("", ask_selected_router)
ai_api.add_router("", summarize_chapter_router)
ai_api.add_router("", image_search_router)