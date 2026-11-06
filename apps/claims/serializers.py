from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Claim, ClaimHistory, ResolutionProofImage


class ClaimHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimHistory
        fields = ['id', 'old_status', 'new_status', 'created_at']


class ResolutionProofImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ResolutionProofImage
        fields = ['id', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


def _display_name(user):
    profile = getattr(user, 'profile', None)
    if profile is not None:
        parts = [profile.prenom, profile.nom]
        name = ' '.join(p.strip() for p in parts if p and p.strip())
        if name:
            return name

    name = (user.get_full_name() or '').strip()
    return name or user.get_username()


class AssignedSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return _display_name(user)


class ClaimSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    service_label = serializers.SerializerMethodField()
    history = ClaimHistorySerializer(many=True, read_only=True)
    assigned_to = AssignedSerializer(read_only=True)
    resolution_proofs = ResolutionProofImageSerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id', 'reference', 'title', 'description', 'category', 'category_label',
            'service_label', 'assigned_to', 'status', 'priority',
            'latitude', 'longitude', 'address',
            'location_accuracy', 'location_source',  # ✅ AJOUTÉ
            'created_at', 'updated_at', 'history',
            'resolution_comment', 'resolution_proofs',
        ]
        read_only_fields = ['reference', 'status', 'created_at', 'updated_at']

    def get_service_label(self, claim):
        return claim.service.name if claim.service_id else None