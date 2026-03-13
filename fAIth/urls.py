"""
URL configuration for fAIth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI
from backend.api import healcheck_api, backend_api
from ai.api import ai_api

# Create NinjaAPI instance with custom namespace for simpler reverse() calls
api = NinjaAPI(urls_namespace="api")

# Register routers with the API
api.add_router("", healcheck_api)
api.add_router("", backend_api)
api.add_router("v1/", ai_api)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls')),
    path('', api.urls),
]
