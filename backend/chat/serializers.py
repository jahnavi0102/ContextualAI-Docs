# backend/chat/serializers.py
from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'role', 'content', 'timestamp', 'is_helpful', 'feedback_text']
        read_only_fields = ['id', 'session', 'timestamp', 'is_helpful', 'feedback_text'] 

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

# Your SendMessageSerializer is correct for accepting only 'content'
class SendMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['content']

