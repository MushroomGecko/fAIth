"""
URL configuration for fAIth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI
from backend.urls import router as backend_router
from ai.urls import router as ai_router

# Create NinjaAPI instance with custom namespace for simpler reverse() calls
api = NinjaAPI(urls_namespace="api")

# Register routers with the API
api.add_router("", backend_router)
api.add_router("v1/", ai_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls')),
    path('', api.urls),
]
