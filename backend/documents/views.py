from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentChunk
from rest_framework.response import Response
from rest_framework import status
from .serializers import DocumentSerializer
from .tasks import process_document_task
import django_rq
# from django_q.tasks import async_task


class FileUploadView(generics.CreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        uploaded_file = self.request.data.get('file')
        if uploaded_file is None:
            # This part is good, let it raise the error if no file
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"file": "No file was provided in the request."})

        user = self.request.user
        filename = uploaded_file.name
        metadata = self.request.data.get('metadata', {}) 

        existing_document = Document.objects.filter(user=user, filename=filename).first()

        if existing_document:
            print(f"Replacing existing document: {filename} (ID: {existing_document.id})")
            existing_document.chunks.all().delete()
            existing_document.file = uploaded_file 
            existing_document.size = uploaded_file.size
            existing_document.status = 'pending' 
            existing_document.metadata = metadata 
            existing_document.save()
            return existing_document, "Document updated successfully. Processing in background."
        else:
            print(f"Creating new document: {filename}")
            document = serializer.save(
                user=user, 
                filename=filename, 
                size=uploaded_file.size, 
                metadata=metadata,
                file=uploaded_file
            )
            return document, "Document uploaded successfully. Processing in background."
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document, action_message = self.perform_create(serializer)
        
        django_rq.get_queue('default').enqueue(process_document_task, document.id)
        # async_task('your_app_name.tasks.process_document_task', document.id)
        
        return Response(
            {"message": action_message, "document_id": document.id},
            status=status.HTTP_200_OK # Or HTTP_201_CREATED for new, but 200 is fine
        )

        
class DocumentListView(generics.ListAPIView):
    """
    API endpoint for listing all documents for the authenticated user.
    """
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This method ensures that a user can only see their own documents.
        """
        document = Document.objects.filter(user=self.request.user).first()
        print(DocumentChunk.objects.filter(document=document))
        return Document.objects.filter(user=self.request.user).order_by('-created_at')