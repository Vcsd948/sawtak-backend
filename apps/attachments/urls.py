from django.urls import path
from .views import *

urlpatterns = [
    path('', UploadAttachmentView.as_view()),
    path('claim/<int:claim_id>/', ClaimAttachmentsView.as_view()),
    path('<int:pk>/delete/', DeleteAttachmentView.as_view()),
]