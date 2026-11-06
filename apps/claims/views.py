from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Claim, ClaimHistory, Service, ResolutionProofImage
from .serializers import ClaimSerializer
from ..notifications.services import NotificationService


def _claims_queryset():
    return (
        Claim.objects
        .select_related('service', 'assigned_to', 'assigned_to__profile', 'citizen', 'citizen__profile')
        .prefetch_related('history', 'resolution_proofs', 'attachments') 
    )


class ClaimListCreateView(generics.ListCreateAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # ✅ CORRECTION : Désactive la pagination pour cette vue
    # Cela permet au Super Admin de voir TOUTES les réclamations d'un coup.
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        
        # 1. Super Admin voit ABSOLUMENT TOUT
        if user.is_superuser:
            return _claims_queryset().order_by('-created_at')
            
        # 2. Agent : Voit UNIQUEMENT ses propres réclamations (créées sur Flutter) 
        # ET les réclamations qui lui sont explicitement assignées.
        if user.is_staff:
            return _claims_queryset().filter(
                Q(citizen=user) | Q(assigned_to=user)
            ).order_by('-created_at')
            
        # 3. Citoyen normal : Voit uniquement ses propres réclamations
        return _claims_queryset().filter(citizen=user).order_by('-created_at')

    def perform_create(self, serializer):
        category = serializer.validated_data.get('category', 'autre')
        service = Service.objects.filter(category=category, is_active=True).first()

        with transaction.atomic():
            claim = serializer.save(citizen=self.request.user, service=service)
            ClaimHistory.objects.create(claim=claim, new_status=claim.status)
        NotificationService.notify_claim_created(claim)


class ClaimDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return _claims_queryset()
            
        if user.is_staff:
            # Sécurité : Un agent ne peut voir que ce qui lui est assigné ou ce qu'il a créé
            return _claims_queryset().filter(
                Q(citizen=user) | Q(assigned_to=user)
            )
            
        return _claims_queryset().filter(citizen=user)


class IsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class ClaimStatusSerializer(serializers.Serializer):
    status = serializers.CharField()

    def validate_status(self, value):
        choices = [c[0] for c in Claim._meta.get_field('status').choices]
        if choices and value not in choices:
            raise serializers.ValidationError(
                f"Statut invalide. Valeurs possibles : {', '.join(choices)}"
            )
        return value


class ClaimStatusUpdateView(generics.GenericAPIView):
    serializer_class = ClaimStatusSerializer
    permission_classes = [permissions.IsAuthenticated, IsAgent]
    queryset = _claims_queryset()

    def patch(self, request, *args, **kwargs):
        claim = self.get_object()
        
        # ✅ SÉCURITÉ : Un agent ne peut changer le statut que de ses propres dossiers
        if not request.user.is_superuser and claim.assigned_to != request.user:
            return Response(
                {'error': 'Vous ne pouvez modifier que le statut des réclamations qui vous sont assignées.'},
                status=403
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = claim.status
        new_status = serializer.validated_data['status']

        if new_status == old_status:
            return Response(ClaimSerializer(claim, context={'request': request}).data)

        with transaction.atomic():
            claim.status = new_status
            claim.save(update_fields=['status', 'updated_at'])
            ClaimHistory.objects.create(
                claim=claim,
                old_status=old_status,
                new_status=new_status,
            )

        NotificationService.notify_claim_status_changed(claim, old_status, new_status)

        return Response(ClaimSerializer(claim, context={'request': request}).data)


class ClaimAssignSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField(required=False, allow_null=True)


class ClaimAssignView(generics.GenericAPIView):
    serializer_class = ClaimAssignSerializer
    permission_classes = [permissions.IsAuthenticated, IsAgent]
    queryset = _claims_queryset()

    def patch(self, request, *args, **kwargs):
        # ✅ SÉCURITÉ : Seul le Super Admin peut assigner
        if not request.user.is_superuser:
            return Response(
                {'error': 'Seul le Super Administrateur peut assigner une réclamation.'},
                status=403
            )

        claim = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        agent_id = serializer.validated_data.get('agent_id')
        
        if agent_id:
            try:
                agent = User.objects.get(id=agent_id, is_staff=True)
                claim.assigned_to = agent
                
                # ✅ CORRECTION DU BUG : On gère le statut et l'historique manuellement
                old_status = claim.status
                
                # On passe le statut à "affectée" s'il était en attente ou reçu
                if claim.status in [Claim.STATUS_PENDING, Claim.STATUS_RECEIVED]:
                    claim.status = Claim.STATUS_ASSIGNED
                
                # Sauvegarde en base
                claim.save()
                
                # Historique (si le statut a changé)
                if old_status != claim.status:
                    ClaimHistory.objects.create(
                        claim=claim,
                        old_status=old_status,
                        new_status=claim.status
                    )
                
            except User.DoesNotExist:
                return Response({'error': 'Agent introuvable'}, status=404)
        else:
            # Si on désassigne (agent_id est null)
            claim.assigned_to = None
            claim.save()

        return Response(ClaimSerializer(claim, context={'request': request}).data)


class ClaimResolveSerializer(serializers.Serializer):
    resolution_comment = serializers.CharField(required=True, allow_blank=False)


class ClaimResolveView(generics.GenericAPIView):
    serializer_class = ClaimResolveSerializer
    permission_classes = [permissions.IsAuthenticated, IsAgent]
    parser_classes = (MultiPartParser, FormParser)
    queryset = _claims_queryset()

    def patch(self, request, *args, **kwargs):
        claim = self.get_object()
        
        # ✅ SÉCURITÉ : Un agent ne peut résoudre que ce qui lui est assigné
        if not request.user.is_superuser and claim.assigned_to != request.user:
            return Response(
                {'error': 'Vous ne pouvez résoudre que les réclamations qui vous sont assignées.'},
                status=403
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ✅ VÉRIFICATION : La photo est OBLIGATOIRE
        files = request.FILES.getlist('resolution_proofs')
        if not files:
            return Response(
                {'error': 'Vous devez fournir au moins une photo de preuve de résolution.'}, 
                status=400
            )

        old_status = claim.status
        claim.status = Claim.STATUS_RESOLVED
        
        # ✅ TRAÇABILITÉ : On enregistre qui a résolu la réclamation
        agent_nom = request.user.get_full_name() or request.user.username
        commentaire_final = f"[Résolu par l'agent : {agent_nom}]\n{serializer.validated_data['resolution_comment']}"
        claim.resolution_comment = commentaire_final
        
        with transaction.atomic():
            claim.save(update_fields=['status', 'resolution_comment', 'updated_at'])
            
            # Sauvegarde des photos multiples
            for file in files:
                ResolutionProofImage.objects.create(claim=claim, image=file)
                
            ClaimHistory.objects.create(
                claim=claim, 
                old_status=old_status, 
                new_status=claim.status
            )

        NotificationService.notify_claim_status_changed(claim, old_status, claim.status)
        
        return Response(ClaimSerializer(claim, context={'request': request}).data)