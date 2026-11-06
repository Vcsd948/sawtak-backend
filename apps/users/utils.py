import re


def normalize_phone(raw):
    """
    Normalise un numéro de téléphone mauritanien vers le format stocké en base : '+222XXXXXXXX'.

    Accepte les formats suivants en entrée :
        - 41234567
        - +22241234567
        - 22241234567
        - 00222 41234567
        - 41 23 45 67 (avec espaces/tirets/points/parenthèses)

    Retourne None si l'entrée n'est pas un numéro de téléphone valide
    (ex: c'est un email, ou le format ne correspond à rien de connu).
    """
    if not raw:
        return None

    raw = raw.strip()

    # Si ça ressemble à un email, ce n'est pas un téléphone
    if '@' in raw:
        return None

    # Supprime espaces, tirets, points, parenthèses
    cleaned = re.sub(r'[\s\-\.\(\)]', '', raw)

    # Supprime un préfixe international "00"
    if cleaned.startswith('00'):
        cleaned = cleaned[2:]

    # Retire le préfixe pays "+222" ou "222"
    if cleaned.startswith('+222'):
        cleaned = cleaned[4:]
    elif cleaned.startswith('222') and len(cleaned) > 8:
        cleaned = cleaned[3:]

    # Un numéro mauritanien valide : 8 chiffres commençant par 2, 3 ou 4
    if re.match(r'^[2-4]\d{7}$', cleaned):
        return '+222' + cleaned

    return None
