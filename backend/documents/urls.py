# backend/documents/urls.py
from django.urls import path
from .views import FileUploadView, DocumentListView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='document-upload'),
    path('', DocumentListView.as_view(), name='document-list'),
]