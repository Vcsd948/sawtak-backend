import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://sms.chinqit.com/api/v2'
TIMEOUT_SECONDS = 15


class ChinqitError(Exception):
    """Erreur d'appel à l'API Chinqit."""
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _api_key():
    return (getattr(settings, 'CHINQIT_API_KEY', '') or '').strip()


def _clean_phone(phone):
    """
    ✅ Nettoie le numéro pour s'assurer qu'il est au format +222XXXXXXXX.
    C'est crucial pour que Chinqit retrouve la session lors de la vérification.
    """
    if not phone:
        return None
    # On ne garde que les chiffres
    digits = ''.join(c for c in str(phone) if c.isdigit())
    
    # Si le numéro commence par 222 et fait 11 chiffres (ex: 22241234567)
    if digits.startswith('222') and len(digits) == 11:
        return f'+{digits}'
    
    # Si c'est un numéro mauritanien à 8 chiffres (ex: 41234567)
    if len(digits) == 8 and re.match(r'^[234]\d{7}$', digits):
        return f'+222{digits}'
    
    # Si le numéro est déjà au format +222XXXXXXXX (11 chiffres avec le +)
    if len(digits) == 11 and digits.startswith('222'):
        return f'+{digits}'
        
    return None


def send_verification(phone_number):
    """
    Envoie un code OTP via l'API Chinqit.
    Retourne le numéro de téléphone normalisé (utilisé comme identifiant de session).
    """
    api_key = _api_key()
    if not api_key:
        raise ChinqitError('Clé API Chinqit non configurée')

    normalized_phone = _clean_phone(phone_number)
    if not normalized_phone:
        raise ChinqitError('Numéro de téléphone invalide')

    payload = {
        "phoneNumber": normalized_phone,
        "channel": "sms",
        "language": "fr"
    }

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{DEFAULT_BASE_URL}/code",
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SECONDS
        )
        
        if response.status_code == 200:
            # On retourne le numéro nettoyé pour le stocker en base
            return normalized_phone
        else:
            logger.error(f"Erreur Chinqit send : {response.status_code} - {response.text}")
            raise ChinqitError(f"Erreur Chinqit ({response.status_code})", status=response.status_code)
            
    except requests.exceptions.RequestException as e:
        logger.exception("Chinqit injoignable")
        raise ChinqitError("Service SMS momentanément indisponible.")


def check_verification(phone_number, code):
    """
    Vérifie le code OTP saisi par l'utilisateur via l'API Chinqit.
    Retourne True si le code est correct, False sinon.
    """
    api_key = _api_key()
    if not api_key:
        raise ChinqitError('Clé API Chinqit non configurée')

    normalized_phone = _clean_phone(phone_number)
    if not normalized_phone:
        return False

    payload = {
        "phoneNumber": normalized_phone,
        "code": code
    }

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{DEFAULT_BASE_URL}/check",
            json=payload,
            headers=headers,
            timeout=TIMEOUT_SECONDS
        )
        
        if response.status_code == 200:
            data = response.json()
            # Selon la doc Chinqit, le champ peut être 'success', 'valid' ou 'verified'
            return bool(data.get('success') or data.get('valid') or data.get('verified'))
        elif response.status_code in (400, 404):
            # Code invalide ou expiré
            return False
        else:
            logger.error(f"Erreur Chinqit check : {response.status_code} - {response.text}")
            raise ChinqitError(f"Erreur Chinqit ({response.status_code})", status=response.status_code)
            
    except requests.exceptions.RequestException as e:
        logger.exception("Chinqit injoignable")
        raise ChinqitError("Service SMS momentanément indisponible.")