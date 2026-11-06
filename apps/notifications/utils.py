import firebase_admin
from firebase_admin import credentials, messaging
import os
from django.conf import settings

# Initialisation (à mettre dans une fonction pour éviter les erreurs de chargement)
def init_firebase():
    if not firebase_admin._apps:
        # Téléchargez votre serviceAccountKey.json depuis la console Firebase
        # et placez-le dans backend/config/
        cred_path = os.path.join(settings.BASE_DIR, 'config', 'serviceAccountKey.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

def send_push_notification(user, title, body, data=None):
    init_firebase()
    tokens = user.device_tokens.values_list('token', flat=True)
    
    if not tokens:
        return False

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token,
            )
            messaging.send(message)
        except Exception as e:
            print(f"Erreur d'envoi FCM: {e}")
            # Supprimer le token s'il n'est plus valide
            user.device_tokens.filter(token=token).delete()
            
    return True