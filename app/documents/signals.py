# documents/signals.py
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from .models import Document
import os

@receiver(pre_delete, sender=Document)
def delete_document_file(sender, instance, **kwargs):
    """Elimina il file fisico quando viene eliminato il documento"""
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

@receiver(post_save, sender=Document)
def handle_document_retention(sender, instance, created, **kwargs):
    """Gestisce la retention dei documenti"""
    if created:
        # Imposta data di retention se non presente
        if not instance.retention_date:
            instance.set_retention_period()
            instance.save(update_fields=['retention_date'])