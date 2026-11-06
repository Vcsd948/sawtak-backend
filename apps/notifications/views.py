import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken, Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ : notifications de l'utilisateur connecté."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class RegisterDeviceTokenView(APIView):
    """POST /api/notifications/token/  {"token": "...", "platform": "android"}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = str(request.data.get('token') or '').strip()
        platform = str(request.data.get('platform') or 'android').strip()[:20]

        if not token:
            return Response({'error': 'Token requis'}, status=status.HTTP_400_BAD_REQUEST)

        # Le token est unique : si un autre compte l'avait sur ce téléphone
        # (changement de compte), on le rattache au compte actuel.
        _, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user, 'platform': platform},
        )
        logger.info('Token FCM %s (user id=%s)', 'créé' if created else 'mis à jour', request.user.pk)

        return Response(
            {'message': 'Token enregistré'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MarkNotificationAsReadView(APIView):
    """POST, PATCH ou PUT /api/notifications/<pk>/read/"""
    permission_classes = [permissions.IsAuthenticated]

    def _mark(self, request, pk):
        updated = Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        if not updated:
            return Response({'error': 'Notification introuvable'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'message': 'Notification marquée comme lue'})

    def post(self, request, pk):
        return self._mark(request, pk)

    def patch(self, request, pk):
        return self._mark(request, pk)

    def put(self, request, pk):
        return self._mark(request, pk)


class MarkAllNotificationsAsReadView(APIView):
    """POST, PATCH ou PUT /api/notifications/read-all/"""
    permission_classes = [permissions.IsAuthenticated]

    def _mark_all(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'Toutes les notifications sont lues', 'updated': count})

    def post(self, request):
        return self._mark_all(request)

    def patch(self, request):
        return self._mark_all(request)

    def put(self, request):
        return self._mark_all(request)