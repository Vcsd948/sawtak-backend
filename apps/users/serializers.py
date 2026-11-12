from django.contrib.auth.models import User
from rest_framework import serializers
import os
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['nom', 'prenom', 'date_naissance', 'telephone', 'photo', 'email_verified', 'role', 'specialite']


class UserSerializer(serializers.ModelSerializer):
    nom = serializers.CharField(source='profile.nom', read_only=True)
    prenom = serializers.CharField(source='profile.prenom', read_only=True)
    telephone = serializers.CharField(source='profile.telephone', read_only=True)
    date_naissance = serializers.DateField(source='profile.date_naissance', read_only=True)
    is_verified = serializers.BooleanField(source='profile.email_verified', read_only=True)
    
    role = serializers.CharField(source='profile.role', read_only=True)
    specialite = serializers.CharField(source='profile.specialite', read_only=True)

    photo = serializers.SerializerMethodField()
    fullName = serializers.SerializerMethodField()
    photoUrl = serializers.SerializerMethodField()
    
    username = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'is_staff', 'is_superuser',
            'nom', 'prenom', 'telephone', 'date_naissance', 'is_verified',
            'photo', 'fullName', 'photoUrl', 'role', 'specialite',
        ]

    def get_username(self, obj):
        return obj.email

    def get_photo(self, obj):
        profile = getattr(obj, 'profile', None)
        
        if profile and profile.photo:
            # ✅ Construction robuste de l'URL
            url = profile.photo.url
            
            # Si l'URL est déjà absolue, on la renvoie telle quelle
            if url.startswith('http'):
                return url
                
            request = self.context.get('request')
            if request:
                # On force le HTTPS si on est sur Render
                host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
                if host:
                    return f"https://{host}{url}"
                
                # En local, on utilise le build_absolute_uri classique
                return request.build_absolute_uri(url)
                
            return url
        return None

    def get_photoUrl(self, obj):
        return self.get_photo(obj)

    def get_fullName(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            name = f"{profile.prenom} {profile.nom}".strip()
            if name:
                return name
        return obj.email