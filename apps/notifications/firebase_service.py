import logging
import os

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, exceptions as fb_exceptions, messaging

from .models import DeviceToken

logger = logging.getLogger(__name__)

# ID du canal Android : identique à celui créé dans NotificationService (Flutter)
ANDROID_CHANNEL_ID = 'sawtak_channel'


def _get_app():
    """Initialise Firebase Admin une seule fois (idempotent)."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
    if not cred_path or not os.path.exists(cred_path):
        logger.error('Firebase : fichier serviceAccountKey.json introuvable (%s)', cred_path)
        return None

    cred = credentials.Certificate(cred_path)
    return firebase_admin.initialize_app(cred)


def send_push_notification(user, title, body, data=None):
    """
    Envoie un push FCM à tous les appareils de `user`.
    Retourne le nombre d'envois réussis. Ne lève jamais d'exception.
    """
    try:
        app = _get_app()
        if app is None:
            return 0

        tokens = list(
            DeviceToken.objects.filter(user=user).values_list('token', flat=True)
        )
        if not tokens:
            logger.info('Push ignoré : aucun token pour l\'utilisateur %s', user.pk)
            return 0

        # FCM exige que toutes les valeurs de "data" soient des chaînes
        payload = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

        message = messaging.MulticastMessage(
            tokens=tokens,
            # Bloc "notification" : indispensable pour que l'OS affiche
            # le push quand l'app est fermée.
            notification=messaging.Notification(title=title, body=body),
            data=payload,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id=ANDROID_CHANNEL_ID,
                    sound='default',
                    color='#006B3F',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default', badge=1),
                ),
            ),
        )

        response = messaging.send_each_for_multicast(message, app=app)

        # Nettoyage des tokens morts (app désinstallée, token supprimé au logout...)
        dead_tokens = []
        for token, resp in zip(tokens, response.responses):
            if resp.success:
                continue
            exc = resp.exception
            if isinstance(exc, (messaging.UnregisteredError,
                                messaging.SenderIdMismatchError,
                                fb_exceptions.InvalidArgumentError)):
                dead_tokens.append(token)
            else:
                logger.warning('Échec push (token ...%s) : %s', token[-8:], exc)

        if dead_tokens:
            DeviceToken.objects.filter(token__in=dead_tokens).delete()
            logger.info('%d token(s) invalide(s) supprimé(s)', len(dead_tokens))

        logger.info('Push envoyé : %d succès / %d échec(s)',
                    response.success_count, response.failure_count)
        return response.success_count

    except Exception:
        logger.exception('Erreur inattendue lors de l\'envoi du push')
        return 0