from ninja import Router

from ai.views.ask_selected import router as ask_selected_router
from ai.views.definition_search import router as definition_search_router
from ai.views.devotional_chapter import router as devotional_chapter_router
from ai.views.general_question import router as general_question_router
from ai.views.image_search import router as image_search_router
from ai.views.map_search import router as map_search_router
from ai.views.quiz_chapter import router as quiz_chapter_router
from ai.views.search import router as search_router
from ai.views.summarize_chapter import router as summarize_chapter_router
from fAIth.api_tags import APITags

# Aggregate all AI endpoints
ai_api = Router(tags=[APITags.AI])
ai_api.add_router("", ask_selected_router)
ai_api.add_router("", definition_search_router)
ai_api.add_router("", devotional_chapter_router)
ai_api.add_router("", general_question_router)
ai_api.add_router("", image_search_router)
ai_api.add_router("", map_search_router)
ai_api.add_router("", quiz_chapter_router)
ai_api.add_router("", search_router)
ai_api.add_router("", summarize_chapter_router)
