from django.db import models
from django.conf import settings
from django.utils import timezone

class Profile(models.Model):
    ROLE_CHOICES = (
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent'),
        ('super_admin', 'Super Administrateur'),
    )

    # ✅ LISTE COMPLÈTE DES SPÉCIALITÉS
    SPECIALITE_CHOICES = (
        ('Général', 'Général'),
        ('SOMELEC', 'SOMELEC'),
        ('SNDE', 'SNDE'),
        ('Assainissement', 'Assainissement'),
        ('Mairie', 'Mairie'),
        ('Police', 'Police'),
        ('Santé', 'Santé'),
        ('Éducation', 'Éducation'),
        ('Transport', 'Transport'),
        ('Mauritel', 'Mauritel'),
        ('Chinguitel', 'Chinguitel'),
        ('Mattel', 'Mattel'),
        ('Urbanisme', 'Urbanisme'),
        ('Environnement', 'Environnement'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    nom = models.CharField(max_length=100, default='')
    prenom = models.CharField(max_length=100, default='')
    date_naissance = models.DateField(null=True, blank=True)
    telephone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citoyen')
    
    specialite = models.CharField(
        max_length=50, 
        choices=SPECIALITE_CHOICES, 
        blank=True, 
        null=True, 
        help_text="Ex: SOMELEC, SNDE, Police..."
    )

    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"


class VerificationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, blank=True, default='')
    code_type = models.CharField(
        max_length=20,
        choices=[('email', 'Email'), ('password', 'Password'), ('phone', 'Phone (SMS)')],
    )
    verification_id = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and (timezone.now() - self.created_at).total_seconds() < 600