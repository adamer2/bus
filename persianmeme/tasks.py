from . import models
from django.utils import timezone
from LilSholex import celery_app
from django.conf import settings
from LilSholex.functions import async_to_sync_request
from django.db import transaction

@celery_app.task
def revoke_review(meme_id: int):
    models.Meme.objects.filter(id=meme_id, reviewed=False, status=models.Meme.Status.ACTIVE).update(review_admin=None)


@celery_app.task
def check_meme(meme_id: int):
    try:
        meme = models.Meme.objects.select_related('sender').get(id=meme_id, status=models.Meme.Status.PENDING)
    except models.Meme.DoesNotExist:
        return
    if timezone.localtime().hour < 8:
        meme.task_id = check_meme.apply_async((meme_id,), countdown=settings.CHECK_MEME_COUNTDOWN)
        meme.save()
        return
    accept_count = meme.accept_vote.count()
    deny_count = meme.deny_vote.count()
    if accept_count == deny_count == 0:
        meme.task_id = check_meme.apply_async((meme_id,), countdown=settings.CHECK_MEME_COUNTDOWN)
        meme.save()
    else:
        if accept_count >= deny_count:
            async_to_sync_request(settings.MEME_BASE_URL, meme.accept)
        else:
            async_to_sync_request(settings.MEME_BASE_URL, meme.deny)


@celery_app.task
def periodic_playlist_event_handler():
    for event in models.PlaylistEvent.objects.filter(status=models.PlaylistEvent.Status.PENDING).select_related(
        'playlist_member__playlist', 'playlist_voice__voice', 'playlist_voice__playlist'
    ):
        with transaction.atomic():
            match event.type:
                case models.PlaylistEvent.Type.NEW_MEMBER:
                    models.NewMeme.objects.bulk_create(
                        (models.NewMeme(
                            file_id=playlist_voice.voice.file_id,
                            file_unique_id=playlist_voice.voice.file_unique_id,
                            name=playlist_voice.voice.name,
                            sender_id=event.playlist_member.user_id,
                            status=models.NewMeme.Status.ACTIVE,
                            visibility=models.NewMeme.Visibility.PRIVATE,
                            tags=playlist_voice.voice.tags,
                            type=playlist_voice.voice.type,
                            description=playlist_voice.voice.description,
                            playlist_voice=playlist_voice,
                            playlist_member=event.playlist_member
                        ) for playlist_voice in
                            event.playlist_member.playlist.playlist_voices.all().select_related('voice')),
                        1000,
                        True
                    )
                case models.PlaylistEvent.Type.NEW_MEME:
                    models.NewMeme.objects.bulk_create(
                        (models.NewMeme(
                            file_id=event.playlist_voice.voice.file_id,
                            file_unique_id=event.playlist_voice.voice.file_unique_id,
                            name=event.playlist_voice.voice.name,
                            sender_id=user_id,
                            status=models.NewMeme.Status.ACTIVE,
                            visibility=models.NewMeme.Visibility.PRIVATE,
                            tags=event.playlist_voice.voice.tags,
                            type=event.playlist_voice.voice.type,
                            description=event.playlist_voice.voice.description,
                            playlist_voice=event.playlist_voice,
                            playlist_member_id=playlist_member_id
                        ) for playlist_member_id, user_id in
                            event.playlist_voice.playlist.playlist_members.all().values_list('id', 'user_id')),
                        1000,
                        True
                    )
            event.status = models.PlaylistEvent.Status.HANDLED
            event.save(update_fields=('status',))
