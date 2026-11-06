from rest_framework import serializers
from .models import Attachment

class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'claim', 'file', 'file_name', 'file_type', 'created_at', 'file_url', 'thumbnail_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if obj.file and request else None
        
    def get_thumbnail_url(self, obj):
        return self.get_file_url(obj)