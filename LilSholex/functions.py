from .decorators import async_fix
from .exceptions import TooManyRequests
from aiohttp import ClientResponse, ClientSession, ClientTimeout
import json
from .context import telegram as telegram_context
from asgiref.sync import async_to_sync
from django.conf import settings

numbers = {
    '0': '0️⃣',
    '1': '1️⃣',
    '2': '2️⃣',
    '3': '3️⃣',
    '4': '4️⃣',
    '5': '5️⃣',
    '6': '6️⃣',
    '7': '7️⃣',
    '8': '8️⃣',
    '9': '9️⃣'
}


async def handle_request_exception(response: ClientResponse):
    if response.status != 429:
        return True
    raise TooManyRequests((await response.json())['parameters']['retry_after'])


@async_fix
async def answer_callback_query(text: str, show_alert: bool, cache_time: int = 0):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}answerCallbackQuery',
        params={
            'callback_query_id': telegram_context.callback_query.QUERY_ID.get(),
            'text': text,
            'show_alert': str(show_alert),
            'cache_time': cache_time
        }
    ) as response:
        return await handle_request_exception(response)


def emoji_number(string_number: str):
    string = str()
    for digit in string_number:
        string += numbers[digit]
    return string


def handle_message_params(
        message: dict,
        reply_markup: dict | None = None,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None
):
    if reply_markup:
        message['reply_markup'] = json.dumps(reply_markup)
    if reply_to_message_id:
        message['reply_parameters'] = json.dumps(
            {'message_id': reply_to_message_id, 'allow_sending_without_reply': True}
        )
    if parse_mode:
        message['parse_mode'] = parse_mode


@async_fix
async def answer_inline_query(
        results: str,
        next_offset: str,
        switch_pm_text: str,
        switch_pm_parameter: str
):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}answerInlineQuery',
        params={
            'results': results,
            'next_offset': next_offset,
            'switch_pm_text': switch_pm_text,
            'switch_pm_parameter': switch_pm_parameter,
            'inline_query_id': telegram_context.inline_query.QUERY_ID.get(),
            'cache_time': 0
        }
    ) as response:
        await handle_request_exception(response)


@async_fix
async def send_message(chat_id: int, text: str):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}sendMessage',
        params={'chat_id': chat_id, 'text': text}
    ) as response:
        await handle_request_exception(response)


@async_fix
async def edit_message_reply_markup(chat_id: int, new_reply_markup: dict):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}editMessageReplyMarkup',
        params={
            'chat_id': chat_id,
            'reply_markup': json.dumps(new_reply_markup),
            'message_id': telegram_context.common.MESSAGE_ID.get()
        }
    ) as response:
        await handle_request_exception(response)


@async_fix
async def pin_chat_message(chat_id: int, message_id: int):
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}pinChatMessage',
        params={'chat_id': chat_id, 'message_id': message_id}
    ) as response:
        return await handle_request_exception(response)


@async_fix
async def delete_message(chat_id: int) -> bool:
    async with telegram_context.common.HTTP_SESSION.get().get(
        f'{telegram_context.common.BOT_BASE_URL.get()}deleteMessage',
        params={'chat_id': chat_id, 'message_id': telegram_context.common.MESSAGE_ID.get()}
    ) as response:
        return await handle_request_exception(response)


@async_to_sync
async def async_to_sync_request(base_url: str, request_func, *args, **kwargs):
    async with ClientSession(timeout=ClientTimeout(settings.REQUESTS_TIMEOUT)) as session:
        telegram_context.common.HTTP_SESSION.set(session)
        telegram_context.common.BOT_BASE_URL.set(base_url)
        return await request_func(*args, **kwargs)
