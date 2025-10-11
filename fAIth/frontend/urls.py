from django.urls import path
from . import views

urlpatterns = [
    path('<str:book>-<str:chapter>-<str:version>/', views.full_view, name='full_view'),
    path('<str:book>-<str:chapter>/', views.book_chapter_view, name='book_chapter_view'),
    path('<str:book>/', views.book_view, name='book_view'),
    path('', views.default_view, name='default_view')
]
