from django.conf import settings
from django.db import models
import uuid


class Claim(models.Model):
    STATUS_PENDING = 'en_attente'
    STATUS_RECEIVED = 'reçue'
    STATUS_ASSIGNED = 'affectée'
    STATUS_IN_PROGRESS = 'en_cours'
    STATUS_RESOLVED = 'résolue'
    STATUS_REJECTED = 'rejetée'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_RECEIVED, 'Reçue'),
        (STATUS_ASSIGNED, 'Affectée'),
        (STATUS_IN_PROGRESS, 'En cours'),
        (STATUS_RESOLVED, 'Résolue'),
        (STATUS_REJECTED, 'Rejetée'),
    ]
    PRIORITY_CHOICES = [('Basse', 'Basse'), ('Moyenne', 'Moyenne'), ('Haute', 'Haute'), ('Urgente', 'Urgente')]

    CATEGORY_CHOICES = [
        ('electricite', 'Électricité (SOMELEC)'),
        ('eau', 'Eau potable (SNDE)'),
        ('assainissement', 'Assainissement'),
        ('telecom', 'Télécommunications'),
        ('sante', 'Santé'),
        ('education', 'Éducation'),
        ('transport', 'Transport'),
        ('etat_civil', 'État civil'),
        ('commerce', 'Commerce'),
        ('banques', 'Banques'),
        ('urbanisme', 'Urbanisme'),
        ('securite', 'Sécurité'),
        ('emploi', 'Emploi'),
        ('securite_sociale', 'Sécurité sociale'),
        ('environnement', 'Environnement'),
        ('agriculture', 'Agriculture'),
        ('elevage', 'Élevage'),
        ('peche', 'Pêche'),
        ('postes', 'Services postaux'),
        ('administration', 'Administration publique'),
        ('autre', 'Autre'),
    ]

    citizen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='claims')
    reference = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='autre')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Moyenne')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    
    # ✅ NOUVEAUX CHAMPS POUR LA TRAÇABILITÉ GPS
    location_accuracy = models.FloatField(null=True, blank=True, help_text="Précision GPS en mètres")
    location_source = models.CharField(max_length=20, default='gps', help_text="Source : gps, manuelle, inconnue")

    service = models.ForeignKey(
        'Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims',
        limit_choices_to={'is_staff': True},
    )

    resolution_comment = models.TextField(blank=True, null=True, help_text="Commentaire de l'agent sur la résolution")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"REC-{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.title}"

    def mark_assigned(self):
        if self.status not in (self.STATUS_PENDING, self.STATUS_RECEIVED):
            return None
        old_status = self.status
        self.status = self.STATUS_ASSIGNED
        self.save(update_fields=['status', 'updated_at'])
        ClaimHistory.objects.create(
            claim=self,
            old_status=old_status,
            new_status=self.STATUS_ASSIGNED,
        )
        return old_status


class ResolutionProofImage(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='resolution_proofs')
    image = models.ImageField(upload_to='resolutions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Preuve pour {self.claim.reference}"


class Service(models.Model):
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(
        max_length=50,
        choices=Claim.CATEGORY_CHOICES,
        blank=True,
        default='',
        help_text="Les réclamations de cette catégorie sont affectées automatiquement à ce service.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ClaimHistory(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.claim.reference}: {self.old_status} → {self.new_status}"