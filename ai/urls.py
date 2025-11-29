from django.urls import path
from .views import VDBSearchView, LLMCompletionsView

urlpatterns = [
    path('vdb_search/', VDBSearchView.as_view(), name='vdb_search'),
    path('llm_completions/', LLMCompletionsView.as_view(), name='llm_completions'),
]

