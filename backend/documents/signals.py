# backend/documents/signals.py
import os
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from .models import Document # Import your Document model

@receiver(pre_save, sender=Document)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem when corresponding `Document` object is updated
    with new file.
    """
    if not instance.pk: # Object is being created, no old file to delete
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).file
    except sender.DoesNotExist:
        return False # Object doesn't exist in DB, nothing to compare
    
    new_file = instance.file
    if not old_file == new_file: # Check if the file field has actually changed
        if os.path.isfile(old_file.path):
            print(f"Deleting old file: {old_file.path}")
            os.remove(old_file.path)

@receiver(post_delete, sender=Document)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem when corresponding `Document` object is deleted.
    """
    if instance.file: # Check if a file is associated
        if os.path.isfile(instance.file.path):
            print(f"Deleting file on document deletion: {instance.file.path}")
            os.remove(instance.file.path)