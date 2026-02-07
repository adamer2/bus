from django.conf import settings
from LilSholex import decorators
from LilSholex.functions import handle_request_exception
from . import models, context as meme_context
from .translations import user_messages
from asgiref.sync import sync_to_async
from aiohttp import ClientSession, TCPConnector, ClientError, ClientTimeout
from django.core.paginator import Paginator
import asyncio
from django import db
from .types import ObjectType
from random import randint
from django.utils.html import escape
from asyncio import TaskGroup
from .keyboards import make_list, make_complete_meme_list
from django.db import transaction
from LilSholex.context import telegram as telegram_context


@decorators.async_fix
async def delete_vote(message_id: int):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'https://api.telegram.org/bot{settings.MEME_TOKEN}/deleteMessage',
        params={'chat_id': settings.MEME_CHANNEL, 'message_id': message_id}
    ) as response:
        await handle_request_exception(response)


@sync_to_async
def get_page(broadcast: models.Broadcast):
    db.close_old_connections()
    result = tuple(models.User.objects.filter(started=True).exclude(
        last_broadcast=broadcast
    )[:settings.PAGINATION_LIMIT])
    if result:
        models.User.objects.filter(
            id__gte=result[0].id, id__lte=result[-1].id, started=True
        ).update(last_broadcast=broadcast)
    return result


async def perform_broadcast(broadcast: models.Broadcast):
    from_chat_id = broadcast.sender.chat_id
    message_id = broadcast.message_id
    async with ClientSession(timeout=ClientTimeout(settings.REQUESTS_TIMEOUT), connector=TCPConnector(
        limit=settings.BROADCAST_CONNECTION_LIMIT, ttl_dns_cache=settings.DNS_CACHE_TIME
    )) as client:
        async def forwarder(chat_id: int):
            while True:
                try:
                    async with client.get(
                        f'https://api.telegram.org/bot{settings.MEME_TOKEN}/copyMessage',
                        params={'from_chat_id': from_chat_id, 'chat_id': chat_id, 'message_id': message_id}
                    ) as request_result:
                        if request_result.status != 429:
                            break
                        await asyncio.sleep((await request_result.json())['parameters']['retry_after'])
                except (ClientError, asyncio.TimeoutError):
                    pass

        while result := await get_page(broadcast):
            first_index = 0
            for last_index in range(settings.BROADCAST_LIMIT, settings.PAGINATION_LIMIT + 1, settings.BROADCAST_LIMIT):
                async with TaskGroup() as tg:
                    for user in result[first_index:last_index]:
                        tg.create_task(forwarder(user.chat_id))
                    tg.create_task(asyncio.sleep(0.7))
                first_index = last_index


def make_result(meme: list, caption: str | None):
    temp_result = {
        'id': meme[0]
    }
    if meme[3] == models.MemeType.VIDEO:
        temp_result['type'] = 'video'
        temp_result['video_file_id'] = meme[1]
        temp_result['title'] = meme[2]
        if caption:
            temp_result['caption'] = f'<b>{escape(caption)}</b>'
            temp_result['parse_mode'] = 'HTML'
            temp_result['description'] = caption
        elif meme[4]:
            temp_result['description'] = meme[4]
    else:
        temp_result['type'] = 'voice'
        temp_result['voice_file_id'] = meme[1]
        if caption:
            temp_result['caption'] = f'<b>{escape(caption)}</b>'
            temp_result['parse_mode'] = 'HTML'
            temp_result['title'] = f'{meme[2]} ({caption})'
        else:
            temp_result['title'] = meme[2]
    return temp_result


def make_like_result(meme: list, caption: str | None):
    temp_result = make_result(meme, caption)
    temp_result['reply_markup'] = {'inline_keyboard': [[
        {'text': '👍', 'callback_data': f'up:{meme[0]}'}, {'text': '👎', 'callback_data': f'down:{meme[0]}'}
    ]]}
    return temp_result


def make_meme_result(meme: models.Meme, caption: str | None):
    temp_result = {
        'id': meme.id
    }
    if meme.type == models.MemeType.VIDEO:
        temp_result['type'] = 'video'
        temp_result['video_file_id'] = meme.file_id
        temp_result['title'] = meme.name
        if caption:
            temp_result['caption'] = f'<b>{escape(caption)}</b>'
            temp_result['parse_mode'] = 'HTML'
            temp_result['description'] = caption
        elif meme.description:
            temp_result['description'] = temp_result['description'] = meme.description
    else:
        temp_result['type'] = 'voice'
        temp_result['voice_file_id'] = meme.file_id
        if caption:
            temp_result['caption'] = f'<b>{escape(caption)}</b>'
            temp_result['parse_mode'] = 'HTML'
            temp_result['title'] = f'{meme.name} ({caption})'
        else:
            temp_result['title'] = meme.name
    return temp_result


def make_meme_like_result(meme: models.Meme, caption: str | None):
    temp_result = make_meme_result(meme, caption)
    temp_result['reply_markup'] = {'inline_keyboard': [[
        {'text': '👍', 'callback_data': f'up:{meme.id}'}, {'text': '👎', 'callback_data': f'down:{meme.id}'}
    ]]}
    return temp_result


@sync_to_async
def make_list_string(object_type: ObjectType, objs):
    if objs.exists():
        return '\n\n'.join([
            f'{"🔴" if object_type in (ObjectType.PLAYLIST, ObjectType.PLAYLIST_MEMBER) 
            else ("🔊" if obj.type == models.MemeType.VOICE else "📹")}'
            f' {index + 1} : {obj.name}' for index, obj in enumerate(objs)
        ])
    match object_type:
        case ObjectType.PLAYLIST:
            return user_messages['no_playlist']
        case ObjectType.PLAYLIST_MEMBER:
            return user_messages['no_playlist_member']
        case ObjectType.PLAYLIST_VOICE | ObjectType.PRIVATE_VOICE | ObjectType.SUGGESTED_VOICE | \
             ObjectType.PLAYLIST_MEMBER_VOICE:
            return user_messages['no_voice']
        case ObjectType.SUGGESTED_VIDEO:
            return user_messages['no_video']
        case ObjectType.SUGGESTED_MEME:
            return user_messages['empty_list']


async def make_string_keyboard_list(object_type: ObjectType, objs, prev_page: int, next_page: int):
    async with TaskGroup() as tg:
        string_list = tg.create_task(make_list_string(object_type, objs))
        keyboard_list = tg.create_task(make_list(object_type, objs, prev_page, next_page))
    return string_list.result(), keyboard_list.result()


async def make_string_meme_keyboard_list(object_type: ObjectType, memes, prev_page: int | None, next_page: int | None):
    async with TaskGroup() as tg:
        string_list = tg.create_task(make_list_string(object_type, memes))
        keyboard_list = tg.create_task(make_complete_meme_list(object_type, memes, prev_page, next_page))
    return string_list.result(), keyboard_list.result()


def paginate(objs):
    paginator = Paginator(objs, 9)
    if not paginator.num_pages:
        return (), None, None
    page = paginator.page(page) if (page := meme_context.callback_query.PAGE.get()) <= paginator.num_pages \
        else paginator.page(paginator.num_pages)
    return (
        page.object_list,
        page.previous_page_number() if page.has_previous() else None,
        page.next_page_number() if page.has_next() else None
    )


async def get_message():
    try:
        target_message = await models.Message.objects.select_related('sender').aget(
            id=meme_context.callback_query.MESSAGE_ID.get(), status=models.Message.Status.PENDING
        )
    except models.Message.DoesNotExist:
        return False
    target_message.status = models.Message.Status.READ
    await target_message.asave(update_fields=('status',))
    return target_message


def check_for_voice():
    return 'voice' in (message := telegram_context.message.MESSAGE.get()) and (
            'mime_type' not in message['voice'] or message['voice']['mime_type'] == 'audio/ogg'
    )


def check_for_video(bypass_limits: bool):
    return 'video' in (message := telegram_context.message.MESSAGE.get()) and (
        'mime_type' not in (video := message['video']) or video['mime_type'] == 'video/mp4'
    ) and (bypass_limits or (video['file_size'] <= settings.VIDEO_SIZE_LIMIT and
                             video['duration'] <= settings.VIDEO_DURATION_LIMIT))


def create_description(tags):
    return tags.replace('\n', ', ')[:settings.MAX_DESCRIPTION_LENGTH]


def fake_deny_vote(queryset):
    if (user_count := models.User.objects.count()) < settings.MIN_FAKE_VOTE:
        fake_min = user_count
        fake_max = user_count
    else:
        fake_min = settings.MIN_FAKE_VOTE
        if user_count < settings.MAX_FAKE_VOTE:
            fake_max = user_count
        else:
            fake_max = settings.MAX_FAKE_VOTE
    faked_count = 0
    for meme in queryset:
        if meme.status == meme.Status.PENDING and \
                meme.deny_vote.count() < (random_fake := randint(fake_min, fake_max)):
            faked_count += 1
            meme.deny_vote.set(models.User.objects.all()[:random_fake])
    return faked_count


def clean_query(query):
    new_query = str()
    for char in query:
        if char not in settings.SENSITIVE_CHARACTERS:
            new_query += char
    return new_query.strip()


@sync_to_async
def set_meme_message_id(meme_id: int, message_id: int) -> bool:
    with transaction.atomic():
        try:
            meme = models.Meme.objects.select_for_update(of=('self', 'newmeme_ptr')).get(
                id=meme_id, status=models.Meme.Status.PENDING
            )
        except models.Meme.DoesNotExist:
            return False
        meme.message_id = message_id
        meme.save(update_fields=('message_id',))
        return True
