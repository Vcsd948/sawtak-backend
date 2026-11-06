from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    CheckAvailabilityView,  # ✅ IMPORT AJOUTÉ
    ProfileView,
    UpdateProfilePhotoView,
    VerifyEmailView,
    ResendEmailCodeView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    SmsPasswordResetCheckView,
    SmsPasswordResetRequestView,
    SmsPasswordResetConfirmView,
    AgentListView,
    CitoyenListView,
    PromoteAgentView,
    RevokeAgentView,
)

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('check-availability/', CheckAvailabilityView.as_view(), name='check-availability'), # ✅ ROUTE AJOUTÉE
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('me/photo/', UpdateProfilePhotoView.as_view(), name='update-photo'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-email-code/', ResendEmailCodeView.as_view(), name='resend-email-code'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/sms/check/', SmsPasswordResetCheckView.as_view(), name='sms-reset-check'),
    path('password-reset/sms/request/', SmsPasswordResetRequestView.as_view(), name='sms-reset-request'),
    path('password-reset/sms/confirm/', SmsPasswordResetConfirmView.as_view(), name='sms-reset-confirm'),
    
    path('agents/', AgentListView.as_view(), name='agents-list'),
    path('citoyens/', CitoyenListView.as_view(), name='citoyens-list'),
    path('promote-agent/', PromoteAgentView.as_view(), name='promote-agent'), 
    path('revoke-agent/', RevokeAgentView.as_view(), name='revoke-agent'),
]