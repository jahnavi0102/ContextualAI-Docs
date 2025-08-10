from django.db import models
from users.models import User

# Define the choices for user actions as an enum-like class
class ActionChoices(models.IntegerChoices):
    DOCUMENT_UPLOAD = 1, "Document Upload"
    CHAT_START = 2, "Chat Start"
    DOCUMENT_VIEW = 3, "Document View"

class SearchQuery(models.Model):
    """
    Logs user search queries.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_queries')
    query = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search by {self.user.email}: {self.query[:50]}..."

    class Meta:
        verbose_name = "Search Query"
        verbose_name_plural = "Search Queries"
        ordering = ['-timestamp']

class UserActivity(models.Model):
    """
    Logs various user actions within the application.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.IntegerField(choices=ActionChoices.choices)
    resource_id = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']