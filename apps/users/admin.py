from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, VerificationCode

# On ajoute le Profil directement dans la page de l'utilisateur
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil (Spécialité, Téléphone...)'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'get_specialite')
    
    def get_specialite(self, obj):
        return obj.profile.specialite if hasattr(obj, 'profile') else '-'
    get_specialite.short_description = 'Spécialité'

# On remplace l'admin User de base par le nôtre
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nom', 'prenom', 'telephone', 'specialite', 'email_verified')
    list_filter = ('specialite', 'email_verified')
    search_fields = ('user__username', 'user__email', 'nom', 'prenom', 'telephone')

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code_type', 'code', 'is_used', 'created_at')
    list_filter = ('code_type', 'is_used')