"""
URL configuration for fAIth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from frontend import views

urlpatterns = [
    path('<str:book>-<str:chapter>-<str:version>/', views.full_view, name='full_view'),
    path('<str:book>-<str:chapter>/', views.book_chapter_view, name='book_chapter_view'),
    path('<str:book>/', views.book_view, name='book_view'),
    path('', views.default_view, name='default_view'),
    path('admin/', admin.site.urls),
]
