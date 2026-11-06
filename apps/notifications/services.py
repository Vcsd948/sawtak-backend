from .firebase_service import send_push_notification
from .models import Notification


class NotificationService:
    @staticmethod
    def notify_claim_created(claim):
        Notification.objects.create(
            user=claim.citizen,
            title="Réclamation reçue",
            body=f"Votre réclamation '{claim.title}' a bien été enregistrée.",
            type="claim_created"
        )

    @staticmethod
    def notify_claim_status_changed(claim, old_status, new_status):
        title = "Mise à jour de votre réclamation"
        body = f"Le statut de '{claim.title}' est passé à '{new_status}'."

        # 1) Notification enregistrée en base (liste dans l'app)
        Notification.objects.create(
            user=claim.citizen,
            title=title,
            body=body,
            type="claim_status"
        )

        # 2) Push FCM vers les téléphones du citoyen
        send_push_notification(
            user=claim.citizen,
            title=title,
            body=body,
            data={
                'type': 'claim_status',
                'claim_id': claim.pk,
                'old_status': old_status,
                'new_status': new_status,
            },
        )