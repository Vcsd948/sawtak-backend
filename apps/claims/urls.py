from django.urls import path
from .views import (
    ClaimListCreateView,
    ClaimDetailView,
    ClaimStatusUpdateView,
    ClaimAssignView,
    ClaimResolveView,
)

urlpatterns = [
    path('', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('<int:pk>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('<int:pk>/status/', ClaimStatusUpdateView.as_view(), name='claim-status-update'),
    path('<int:pk>/assign/', ClaimAssignView.as_view(), name='claim-assign'),
    path('<int:pk>/resolve/', ClaimResolveView.as_view(), name='claim-resolve'),
]