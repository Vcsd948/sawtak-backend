from django.db import models
from ..claims.models import Claim

class Attachment(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            ext = self.file_name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif']: self.file_type = 'image'
            elif ext in ['pdf', 'doc']: self.file_type = 'document'
            else: self.file_type = 'other'
        super().save(*args, **kwargs)