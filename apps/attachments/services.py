import os
import logging
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from .models import Attachment

logger = logging.getLogger(__name__)


class AttachmentService:
    """
    Service de gestion des pièces jointes
    """

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo
    ALLOWED_MIME_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/webm',
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    ALLOWED_EXTENSIONS = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.mp4', '.mov', '.webm',
        '.pdf', '.doc', '.docx',
    ]
    THUMBNAIL_SIZE = (200, 200)

    @staticmethod
    def get_file_type(file):
        """
        Détermine le type de fichier à partir du MIME type
        """
        mime_type = file.content_type or 'application/octet-stream'
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type in ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'document'
        return 'other'

    @staticmethod
    def validate_file(file):
        """
        Valide le fichier (taille, type, extension)
        """
        # Vérifier la taille
        if file.size > AttachmentService.MAX_FILE_SIZE:
            raise ValueError(f"Le fichier est trop volumineux. Taille max: {AttachmentService.MAX_FILE_SIZE / (1024 * 1024)} Mo")

        # Vérifier le type MIME
        mime_type = file.content_type or 'application/octet-stream'
        if mime_type not in AttachmentService.ALLOWED_MIME_TYPES:
            raise ValueError("Type de fichier non autorisé")

        # Vérifier l'extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in AttachmentService.ALLOWED_EXTENSIONS:
            raise ValueError("Extension de fichier non autorisée")

        return True

    @staticmethod
    def generate_thumbnail(attachment):
        """
        Génère une vignette JPEG (200x200 max) pour un Attachment de type
        image, et la sauvegarde sur son champ `thumbnail`.

        Important : on relit le fichier déjà écrit sur le stockage
        (`attachment.file`), pas le flux d'upload d'origine. Ce dernier a
        déjà été entièrement consommé par Django au moment de
        l'enregistrement de l'Attachment (FileField.pre_save lit tout le
        flux pour l'écrire sur disque) — le rouvrir donnerait un flux vide
        et ferait échouer PIL silencieusement.

        Ne bloque jamais l'upload : retourne False en cas d'échec, l'image
        elle-même reste disponible via `attachment.file`.
        """
        if attachment.file_type != 'image':
            return False

        try:
            with attachment.file.open('rb') as source:
                img = Image.open(source)
                img.load()  # force la lecture avant que le fichier ne se referme

            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail(AttachmentService.THUMBNAIL_SIZE)

            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            thumb_filename = f"thumb_{os.path.splitext(os.path.basename(attachment.file.name))[0]}.jpg"
            attachment.thumbnail.save(thumb_filename, ContentFile(buffer.read()), save=True)
            return True

        except Exception as e:
            logger.warning(
                "Échec de génération de la vignette pour l'attachement %s: %s",
                attachment.id, e,
            )
            return False
