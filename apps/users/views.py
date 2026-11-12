import logging
import secrets
from html import escape

import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .backends import find_user_by_identifier, phone_key, phone_regex
from .chinqit_client import ChinqitError, check_verification, send_verification
from .models import Profile, VerificationCode
from .serializers import UserSerializer
from .utils import normalize_phone

logger = logging.getLogger(__name__)

MSG_INVALID_CODE = 'Code invalide ou expiré'
MSG_LOGIN_FAILED = 'Identifiants incorrects. Vérifiez votre email ou numéro de téléphone et votre mot de passe.'
MSG_EMAIL_UNAVAILABLE = "L'email n'a pas pu être envoyé. Réessayez dans un instant ou utilisez la réinitialisation par SMS."
MSG_ACCES_REFUSE = 'Accès refusé'
MSG_USER_NOT_FOUND = 'Utilisateur introuvable'
MSG_SMS_UNAVAILABLE = 'Service SMS momentanément indisponible. Réessayez dans un instant.'
MSG_NO_ACCOUNT_PHONE = 'Aucun compte trouvé avec ce numéro'
MSG_TOO_MANY_ATTEMPTS = 'Trop de tentatives. Réessayez plus tard.'
MSG_NO_PHONE_ON_ACCOUNT = 'Aucun numéro de téléphone associé à ce compte'


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def session_payload(user, request, **extra):
    access, refresh = get_tokens(user)
    return {
        **extra,
        'access': access,
        'refresh': refresh,
        'user': UserSerializer(user, context={'request': request}).data,
    }


def generate_code():
    return str(secrets.randbelow(900000) + 100000)


def phone_digits_key(raw):
    digits = ''.join(ch for ch in str(raw or '') if ch.isdigit())
    return digits[-8:] if len(digits) >= 8 else ''


def phone_to_e164(raw):
    key = phone_digits_key(raw)
    return f'+222{key}' if key else None


def build_code_email(heading, intro, code):
    heading_h = escape(heading)
    intro_h = escape(intro)
    code_h = escape(code)
    html = (
        '<div style="margin:0;padding:24px 12px;background:#F7FAF8;'
        'font-family:Arial,Helvetica,sans-serif;">'
        '<div style="max-width:480px;margin:0 auto;background:#ffffff;'
        'border-radius:20px;overflow:hidden;border:1px solid #E2E8E4;">'
        '<div style="background:#006B3F;'
        'background:linear-gradient(135deg,#004D2C,#006B3F,#00875A);'
        'padding:28px 24px;text-align:center;">'
        '<div style="color:#ffffff;font-size:26px;font-weight:800;">Sawtak</div>'
        '<div style="color:#F4D06F;font-size:16px;margin-top:2px;">صوتك</div>'
        '</div>'
        '<div style="padding:28px 24px;color:#0F1A14;">'
        f'<h2 style="margin:0 0 10px 0;font-size:20px;color:#004D2C;">{heading_h}</h2>'
        f'<p style="margin:0;font-size:15px;line-height:1.55;color:#4A5A52;">{intro_h}</p>'
        '<div style="text-align:center;margin:26px 0;">'
        '<span style="display:inline-block;background:#E8F5EE;color:#004D2C;'
        'font-size:32px;font-weight:800;letter-spacing:10px;'
        f'padding:14px 22px 14px 32px;border-radius:14px;">{code_h}</span>'
        '</div>'
        '<p style="margin:0;font-size:13px;line-height:1.5;color:#8A9691;">'
        "Ne partagez ce code avec personne. Si vous n'êtes pas à l'origine de "
        'cette demande, ignorez simplement ce message.</p>'
        '</div></div></div>'
    )
    return html


def send_code_email(user, subject, heading, intro, code):
    if not user.email:
        logger.warning("Envoi email impossible : l'utilisateur id=%s n'a pas d'email", user.id)
        return False

    api_key = getattr(settings, 'SENDLIBERTY_API_KEY', None)
    if not api_key:
        logger.error("SENDLIBERTY_API_KEY manquante dans settings.py / .env")
        return False

    html_content = build_code_email(heading, intro, code)

    payload = {
        "from": "Sawtak <aishaaliou2012@gmail.com>",
        "to": user.email,
        "subject": subject,
        "html": html_content
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://sendliberty.com/api/send",
            json=payload,
            headers=headers,
            timeout=20
        )
        if response.status_code == 200:
            logger.info("Email '%s' envoyé via Sendliberty (user id=%s)", subject, user.id)
            return True
        else:
            logger.error("Erreur Sendliberty (%s) : %s", response.status_code, response.text)
            return False
    except requests.exceptions.RequestException:
        logger.exception("Échec de la connexion à Sendliberty (user id=%s)", user.id)
        return False


class PhoneCodeResendThrottle(AnonRateThrottle):
    scope = 'phone_code_resend'
    rate = '20/hour'


def send_phone_code(user):
    profile = Profile.objects.filter(user=user).first()
    to = phone_to_e164(profile.telephone if profile else '')
    if not to:
        return 'no_phone'
    
    try:
        normalized_phone = send_verification(to)
    except ChinqitError as e:
        logger.error('Envoi SMS Chinqit échoué (user id=%s) : %s', user.id, e)
        return 'rate_limited' if e.status == 429 else 'unavailable'
        
    VerificationCode.objects.create(user=user, code='', code_type='phone', verification_id=normalized_phone)
    return 'ok'


class PublicAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []


# ═══════════════════════════════════════════════════════════════
# ✅ VUES D'AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════

class CheckAvailabilityView(PublicAPIView):
    def post(self, request):
        username = (request.data.get('username') or '').strip()
        email = (request.data.get('email') or '').strip().lower()
        username_taken = User.objects.filter(username__iexact=username).exists() if username else False
        email_taken = User.objects.filter(email__iexact=email).exists() if email else False
        return Response({'username_taken': username_taken, 'email_taken': email_taken})


class RegisterView(PublicAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    def post(self, request):
        data = request.data
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        telephone = normalize_phone(data.get('telephone'))
        
        if not username:
            return Response({'error': 'Nom d\'utilisateur requis'}, status=400)
        if not email or not password:
            return Response({'error': 'Email et mot de passe sont requis'}, status=400)
        if '@' not in email:
            return Response({'error': 'Adresse email invalide'}, status=400)
        if not phone_digits_key(telephone):
            return Response({'error': 'Numéro de téléphone invalide'}, status=400)
        
        if User.objects.filter(username__iexact=username).exists():
            return Response({'error': 'Ce nom d\'utilisateur est déjà pris'}, status=400)
        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Cet email est déjà utilisé'}, status=400)
            
        key = phone_key(telephone)
        if key and Profile.objects.filter(telephone__regex=phone_regex(key)).exists():
            return Response({'error': 'Ce numéro est déjà utilisé'}, status=400)
            
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                
                # ✅ CORRECTION : On extrait explicitement le fichier photo
                photo_file = request.FILES.get('photo')
                if not photo_file and 'photo' in request.data:
                    # Parfois DRF met le fichier dans request.data au lieu de request.FILES
                    if hasattr(request.data['photo'], 'read'):
                        photo_file = request.data['photo']
                
                profile = Profile.objects.create(
                    user=user, 
                    nom=data.get('nom', ''), 
                    prenom=data.get('prenom', ''),
                    telephone=telephone, 
                    date_naissance=data.get('date_naissance') or None,
                    photo=photo_file, # ✅ On utilise la variable extraite
                    role='citoyen'
                )
                
                # ✅ On s'assure que le fichier est bien écrit sur le disque
                if photo_file:
                    profile.photo.save(photo_file.name, photo_file, save=True)
                
                code = generate_code()
                VerificationCode.objects.create(user=user, code=code, code_type='email')
                sent = send_code_email(
                    user, 
                    'Vérification de votre compte Sawtak', 
                    'Bienvenue sur Sawtak', 
                    'Merci de vous être inscrit. Saisissez ce code pour vérifier votre adresse email.', 
                    code
                )
                
        except Exception as e:
            logger.exception("Erreur d'inscription: %s", str(e))
            return Response({'error': 'Impossible de créer le compte.'}, status=400)
            
        # ✅ CORRECTION CRUCIALE ICI : On rafraîchit l'utilisateur depuis la base
        # pour s'assurer que le champ "photo" est bien chargé en mémoire avant la sérialisation.
        user.refresh_from_db()
        
        # On s'assure que le profil est rechargé avec la photo
        if hasattr(user, 'profile'):
            user.profile.refresh_from_db()

        message = 'Compte créé. Code envoyé par email.' if sent else "Compte créé, mais l'email n'a pas pu être envoyé."
        return Response({
            'message': message, 
            'email_sent': sent,
            'user': UserSerializer(user, context={'request': request}).data 
        }, status=201)


class LoginView(PublicAPIView):
    def post(self, request):
        identifier = (request.data.get('identifier') or request.data.get('email') or request.data.get('username') or '')
        identifier = str(identifier).strip()
        password = request.data.get('password') or ''
        if not identifier or not password:
            return Response({'error': 'Identifiant et mot de passe requis'}, status=400)
        user = authenticate(request=request, username=identifier, password=password)
        if user is None:
            return Response({'error': MSG_LOGIN_FAILED}, status=401)
        return Response(session_payload(user, request))


class VerifyEmailView(PublicAPIView):
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        code = str(request.data.get('code') or '').strip()
        
        if not code.isdigit() or not 4 <= len(code) <= 8:
            return Response({'error': MSG_INVALID_CODE}, status=400)
            
        user = User.objects.filter(email__iexact=email).order_by('id').first()
        if not user:
            return Response({'error': MSG_INVALID_CODE}, status=400)
            
        try:
            v_code = VerificationCode.objects.filter(user=user, code=code, code_type='email', is_used=False).latest('created_at')
        except VerificationCode.DoesNotExist:
            return Response({'error': MSG_INVALID_CODE}, status=400)
            
        if not v_code.is_valid():
            return Response({'error': MSG_INVALID_CODE}, status=400)
            
        v_code.is_used = True
        v_code.save()
        
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save()
        
        return Response({'verified': True})


class ResendEmailCodeView(PublicAPIView):
    throttle_classes = [PhoneCodeResendThrottle]
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        user = User.objects.filter(email__iexact=email).order_by('id').first()
        if not user:
            return Response({'error': MSG_USER_NOT_FOUND}, status=404)
            
        code = generate_code()
        VerificationCode.objects.create(user=user, code=code, code_type='email')
        
        sent = send_code_email(
            user, 
            'Vérification de votre compte Sawtak', 
            'Nouveau code de vérification', 
            'Voici votre nouveau code de vérification.', 
            code
        )
        
        if not sent:
            return Response({'error': MSG_EMAIL_UNAVAILABLE}, status=503)
            
        return Response({'message': 'Code renvoyé par email'})


class PasswordResetRequestView(PublicAPIView):
    def post(self, request):
        identifier = (request.data.get('identifier') or '').strip()
        if not identifier:
            return Response({'error': 'Identifiant requis'}, status=400)
        user = find_user_by_identifier(identifier)
        if not user:
            return Response({'error': 'Aucun compte trouvé avec cet identifiant'}, status=404)
        code = generate_code()
        VerificationCode.objects.create(user=user, code=code, code_type='password')
        sent = send_code_email(user, 'Réinitialisation de votre mot de passe Sawtak', 'Réinitialisation du mot de passe', 'Vous avez demandé à réinitialiser votre mot de passe Sawtak. Saisissez ce code dans l\'application pour continuer.', code)
        if not sent:
            return Response({'error': MSG_EMAIL_UNAVAILABLE}, status=503)
        return Response({'message': 'Code envoyé'})


class PasswordResetVerifyView(PublicAPIView):
    def post(self, request):
        identifier = (request.data.get('identifier') or '').strip()
        code = str(request.data.get('code') or '').strip()
        new_password = request.data.get('new_password') or ''
        if not identifier or not code or not new_password:
            return Response({'error': 'Identifiant, code et nouveau mot de passe requis'}, status=400)
        user = find_user_by_identifier(identifier)
        if not user:
            return Response({'error': MSG_USER_NOT_FOUND}, status=404)
        try:
            v_code = VerificationCode.objects.filter(user=user, code=code, code_type='password', is_used=False).latest('created_at')
        except VerificationCode.DoesNotExist:
            return Response({'error': MSG_INVALID_CODE}, status=400)
        if not v_code.is_valid():
            return Response({'error': MSG_INVALID_CODE}, status=400)
        with transaction.atomic():
            user.set_password(new_password)
            user.save()
            VerificationCode.objects.filter(user=user, code_type='password', is_used=False).update(is_used=True)
            profile, _ = Profile.objects.get_or_create(user=user)
            if not profile.email_verified:
                profile.email_verified = True
                profile.save()
        user.refresh_from_db()
        return Response(session_payload(user, request, message='Mot de passe réinitialisé'))


class SmsResetThrottle(AnonRateThrottle):
    scope = 'sms_reset'
    rate = '20/hour'


def find_user_by_phone(raw):
    key = phone_digits_key(raw)
    if not key: return None
    profile = Profile.objects.select_related('user').filter(telephone__endswith=key).first()
    user = profile.user if profile else None
    if user is None:
        candidate = find_user_by_identifier(str(raw).strip())
        if candidate is not None:
            profile = Profile.objects.filter(user=candidate).first()
            if profile and phone_digits_key(profile.telephone) == key:
                user = candidate
    if user is None or not user.is_active: return None
    return user


class SmsPasswordResetCheckView(PublicAPIView):
    throttle_classes = [SmsResetThrottle]
    def post(self, request):
        telephone = (request.data.get('telephone') or '').strip()
        if not phone_digits_key(telephone):
            return Response({'error': 'Numéro de téléphone invalide'}, status=400)
        if find_user_by_phone(telephone) is None:
            return Response({'error': MSG_NO_ACCOUNT_PHONE}, status=404)
        return Response({'message': 'Compte trouvé'})


class SmsPasswordResetRequestView(PublicAPIView):
    throttle_classes = [SmsResetThrottle]
    def post(self, request):
        telephone = (request.data.get('telephone') or '').strip()
        user = find_user_by_phone(telephone)
        if not user:
            return Response({'error': MSG_NO_ACCOUNT_PHONE}, status=404)
        
        result = send_phone_code(user)
        
        if result == 'no_phone':
            return Response({'error': MSG_NO_PHONE_ON_ACCOUNT}, status=400)
        if result == 'rate_limited':
            return Response({'error': MSG_TOO_MANY_ATTEMPTS}, status=429)
        if result != 'ok':
            return Response({'error': MSG_SMS_UNAVAILABLE}, status=503)
            
        return Response({'message': 'Code envoyé par SMS'})


class SmsPasswordResetConfirmView(PublicAPIView):
    throttle_classes = [SmsResetThrottle]
    def post(self, request):
        telephone = (request.data.get('telephone') or '').strip()
        code = str(request.data.get('code') or '').strip()
        new_password = request.data.get('new_password') or ''

        user = find_user_by_phone(telephone)
        if user is None: 
            return Response({'error': MSG_INVALID_CODE}, status=400)

        try:
            is_valid = check_verification(telephone, code)
            if not is_valid:
                return Response({'error': 'Code invalide. Vérifiez le code reçu par SMS.'}, status=400)
        except ChinqitError:
            return Response({'error': MSG_SMS_UNAVAILABLE}, status=503)

        with transaction.atomic():
            user.set_password(new_password)
            user.save()
            VerificationCode.objects.filter(user=user, code_type='password', is_used=False).update(is_used=True)

        user.refresh_from_db()
        logger.info('Mot de passe réinitialisé par SMS (id=%s)', user.id)
        return Response(session_payload(user, request, message='Mot de passe réinitialisé'))


# ───────────────────────── Profil ─────────────────────────
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)


class UpdateProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    def patch(self, request):
        if 'photo' in request.FILES:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.photo = request.FILES['photo']
            profile.save()
            # ✅ On rafraîchit pour être sûr que l'URL est construite avec la nouvelle photo
            request.user.refresh_from_db()
            return Response(UserSerializer(request.user, context={'request': request}).data)
        return Response({'error': 'Aucune photo'}, status=400)


# ───────────────────────── Gestion des Agents (Super Admin) ─────────────────────────
class AgentListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': MSG_ACCES_REFUSE}, status=403)
        
        agents = User.objects.filter(is_staff=True).values(
            'id', 'username', 'email', 'is_superuser', 'is_active', 'profile__specialite', 'profile__role'
        )
        
        data = []
        for a in agents:
            data.append({
                'id': a['id'],
                'username': a['username'],
                'email': a['email'],
                'is_superuser': a['is_superuser'],
                'is_active': a['is_active'],
                'specialite': a['profile__specialite'] or 'Général',
                'role': a['profile__role'] or 'agent'
            })
            
        return Response(data)


class CitoyenListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': MSG_ACCES_REFUSE}, status=403)
        citoyens = User.objects.filter(is_staff=False).values('id', 'username', 'email', 'first_name')
        return Response(citoyens)


class PromoteAgentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': MSG_ACCES_REFUSE}, status=403)
            
        identifier = request.data.get('identifier', '').strip()
        specialite = request.data.get('specialite', 'Général')
        
        if not identifier:
            return Response({'error': 'Veuillez fournir un email ou un téléphone.'}, status=400)

        user = User.objects.filter(
            Q(email__iexact=identifier) | 
            Q(profile__telephone__contains=identifier)
        ).first()
            
        if not user:
            return Response({'error': f'Aucun citoyen trouvé avec : {identifier}.'}, status=404)
        
        if user.is_superuser:
            return Response({'error': 'Cet utilisateur est déjà Super Admin.'}, status=400)
        
        user.is_staff = True
        user.save()
        
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = 'agent'
        profile.specialite = specialite
        profile.save()
        
        return Response({'message': f'✅ {user.username} est maintenant agent {specialite}'})


class RevokeAgentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'Seul un Super Administrateur peut révoquer un agent.'}, status=403)
        
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            
            if user.is_superuser:
                return Response({'error': 'Impossible de révoquer un Super Administrateur.'}, status=400)
                
            user.is_staff = False
            user.save()
            
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = 'citoyen'
            profile.specialite = None
            profile.save()
            
            return Response({'message': f'Les droits de {user.username} ont été révoqués.'})
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable'}, status=404)