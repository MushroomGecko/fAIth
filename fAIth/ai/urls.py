from django.urls import path
from .views import VDBSearchView

urlpatterns = [
    path('vdb_search/', VDBSearchView.as_view(), name='vdb_search'),
]

