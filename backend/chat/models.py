from django.db import models
from users.models import User # Import User model from the auth app

class ChatSession(models.Model):
    """
    Represents a conversational chat session.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True, null=True) # Optional title for the session
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat Session {self.id} for {self.user.email}"

    class Meta:
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"

class ChatMessage(models.Model):
    """
    Represents a single message within a chat session.
    """
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=50) # 'user' or 'ai'
    content = models.TextField()
    is_helpful = models.BooleanField(null=True, blank=True) 
    feedback_text = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True, null=True) 
    

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    class Meta:
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ['timestamp'] # Order messages by time