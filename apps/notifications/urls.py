from django.urls import path
from .views import (
    NotificationListView,
    RegisterDeviceTokenView,
    MarkNotificationAsReadView,
    MarkAllNotificationsAsReadView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('token/', RegisterDeviceTokenView.as_view(), name='register-token'),
    path('<int:pk>/read/', MarkNotificationAsReadView.as_view(), name='mark-read'),
    path('read-all/', MarkAllNotificationsAsReadView.as_view(), name='mark-all-read'),
]