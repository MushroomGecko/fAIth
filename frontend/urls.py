from django.urls import path

from frontend.views import main_site

urlpatterns = [
    path('<str:book>-<str:chapter>-<str:version>/', main_site.full_view, name='full_view'),
    path('<str:book>-<str:chapter>/', main_site.book_chapter_view, name='book_chapter_view'),
    path('<str:book>/', main_site.book_view, name='book_view'),
    path('', main_site.default_view, name='default_view')
]
