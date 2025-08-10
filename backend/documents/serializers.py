# backend/documents/serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'user', 'file', 'filename', 'size', 'created_at', 'status', 'metadata']
        read_only_fields = ['id', 'user', 'filename', 'size', 'created_at', 'status', 'metadata']

    def create(self, validated_data):
        document = Document.objects.create(
            **validated_data
        )
        return document

