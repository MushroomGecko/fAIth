from django.urls import path
from .views import GeneralQuestionView

urlpatterns = [
    path('general_question/', GeneralQuestionView.as_view(), name='general_question'),
]

