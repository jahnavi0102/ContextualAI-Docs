from django.db import models
from users.models import User # Import User model from the auth app

class Document(models.Model):
    """
    Represents an uploaded document.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='documents/', default='')
    filename = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')
    metadata = models.JSONField(default=dict) # To store extracted metadata like file type, etc.
    created_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return self.filename

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

class DocumentChunk(models.Model):
    """
    Represents a chunk of text from a document, used for vector embeddings.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField() # The actual text content of the chunk
    position = models.IntegerField() # Order/position of the chunk within the document

    def __str__(self):
        return f"Chunk {self.position} of {self.document.filename}"

    class Meta:
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        unique_together = ('document', 'position') 