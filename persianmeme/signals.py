from django.dispatch import receiver
from django.db.models.signals import post_save
from . import models


@receiver(post_save, sender=models.PlaylistMember)
def create_playlist_member_event(instance: models.PlaylistMember, created: bool, **kwargs):
    if created:
        instance.playlist_events.create(type=models.PlaylistEvent.Type.NEW_MEMBER)


@receiver(post_save, sender=models.PlaylistVoice)
def create_playlist_voice_event(instance: models.PlaylistVoice, created: bool, **kwargs):
    if created:
        instance.playlist_events.create(type=models.PlaylistEvent.Type.NEW_MEME)
