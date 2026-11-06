import logging
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import Profile

logger = logging.getLogger(__name__)
User = get_user_model()


def phone_key(value):
    """Clé de comparaison d'un numéro : ses 8 derniers chiffres (numéros MR).

    Indépendante du format de stockage : '+22241234567', '0022241234567',
    '41234567', '41 23 45 67' donnent tous '41234567'.
    """
    digits = re.sub(r'\D', '', str(value or ''))
    return digits[-8:] if len(digits) >= 8 else None


def phone_regex(key):
    """Regex PostgreSQL qui retrouve `key` en fin de numéro, quels que soient
    les espaces / tirets intercalés dans la valeur stockée."""
    return r'\D*'.join(key) + r'\D*$'


def find_user_by_identifier(identifier):
    """Retrouve un utilisateur par email ou téléphone (jamais par username)."""
    if identifier is None:
        return None
    identifier = str(identifier).strip()
    if not identifier:
        return None

    if '@' in identifier:
        return User.objects.filter(email__iexact=identifier).order_by('id').first()

    key = phone_key(identifier)
    if not key:
        return None

    profiles = list(
        Profile.objects.select_related('user')
        .filter(telephone__regex=phone_regex(key))[:2]
    )
    if len(profiles) > 1:
        logger.warning('Plusieurs comptes pour le numéro se terminant par %s', key)
        return None
    return profiles[0].user if profiles else None


class EmailOrPhoneModelBackend(ModelBackend):
    """Authentification par email ou téléphone."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (
            username
            or kwargs.get('identifier')
            or kwargs.get('email')
            or kwargs.get(User.USERNAME_FIELD)
        )
        if not identifier or password is None:
            return None

        user = find_user_by_identifier(identifier)
        if user is None:
            User().set_password(password)  # égalise les temps de réponse
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
