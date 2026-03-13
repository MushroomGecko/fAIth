from ninja import Router
from fAIth.api_tags import APITags

healcheck_api = Router(tags=[APITags.HEALTH])
backend_api = Router(tags=[APITags.BACKEND])
