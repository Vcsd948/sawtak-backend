from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Attachment
from .serializers import AttachmentSerializer
from ..claims.models import Claim

class UploadAttachmentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        claim_id = request.data.get('claim_id')
        file = request.FILES.get('file')
        if not claim_id or not file: return Response({'error': 'Données manquantes'}, status=400)
        
        claim = Claim.objects.get(id=claim_id, citizen=request.user)
        att = Attachment.objects.create(claim=claim, file=file)
        return Response(AttachmentSerializer(att, context={'request': request}).data, status=201)

class ClaimAttachmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        # ✅ Si c'est un agent, il voit toutes les photos de la réclamation
        if request.user.is_staff:
            atts = Attachment.objects.filter(claim_id=claim_id)
        else:
            # Si c'est un citoyen, il ne voit que ses propres photos
            atts = Attachment.objects.filter(claim_id=claim_id, claim__citizen=request.user)
            
        return Response(AttachmentSerializer(atts, many=True, context={'request': request}).data)

class DeleteAttachmentView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            if request.user.is_staff:
                att = Attachment.objects.get(pk=pk)
            else:
                att = Attachment.objects.get(pk=pk, claim__citizen=request.user)
            att.file.delete()
            att.delete()
            return Response(status=204)
        except:
            return Response({'error': 'Introuvable'}, status=404)