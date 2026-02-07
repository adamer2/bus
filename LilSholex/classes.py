from aiohttp import ClientSession
from . import models
from .context import telegram as telegram_context
from typing import Any
from .decorators import async_fix
from . import functions
from .exceptions import TooManyRequests
import json
from abc import ABC, abstractmethod
from asyncio import TaskGroup


class BUser(ABC):
    __slots__ = ('chat_id', 'session', '_base_params', 'database')
    session: ClientSession
    _base_params: dict[str, Any]
    database: models.BUser

    def __init__(self, instance: models.BUser = None):
        self.session = telegram_context.common.HTTP_SESSION.get()
        if instance:
            self.database = instance
            self._set_base_params()

    def _set_base_params(self):
        self._base_params = {'chat_id': self.database.chat_id}

    @abstractmethod
    async def set_database_instance(self):
        self._set_base_params()

    @async_fix
    async def send_message(
            self,
            text: str,
            reply_markup: dict = None,
            reply_to_message_id: int | None = None,
            parse_mode: str | None = None,
            disable_web_page_preview: bool = True,
    ) -> int:
        message = {
            **self._base_params,
            'text': text,
            'disable_web_page_preview': str(disable_web_page_preview)
        }
        functions.handle_message_params(message, reply_markup, reply_to_message_id, parse_mode)
        async with self.session.get(
            f'{telegram_context.common.BOT_BASE_URL.get()}sendMessage', params=message
        ) as response:
            if response.status == 200:
                if (result := await response.json())['ok']:
                    return result['result']['message_id']
            elif response.status == 429:
                raise TooManyRequests((await response.json())['parameters']['retry_after'])
            return 0

    async def delete_message(self) -> bool:
        return await functions.delete_message(self.database.chat_id)

    @async_fix
    async def edit_message_text(self, text: str, inline_keyboard: dict = str()):
        if inline_keyboard:
            inline_keyboard = json.dumps(inline_keyboard)
        async with self.session.get(
            f'{telegram_context.common.BOT_BASE_URL.get()}editMessageText',
            params={
                **self._base_params,
                'message_id': telegram_context.common.MESSAGE_ID.get(),
                'text': text,
                'reply_markup': inline_keyboard
            }
        ) as response:
            return await functions.handle_request_exception(response)

    @async_fix
    async def send_animation(
            self,
            animation: str,
            caption: str = str(),
            reply_markup: dict | None = None,
            reply_to_message_id: int | None = None,
            parse_mode: str | None = None
    ):
        message = {**self._base_params, 'animation': animation, 'caption': caption}
        functions.handle_message_params(message, reply_markup, reply_to_message_id, parse_mode)
        async with self.session.get(
            f'{telegram_context.common.BOT_BASE_URL.get()}sendAnimation', params=message
        ) as response:
            return await functions.handle_request_exception(response)

    @async_fix
    async def unpin_chat_message(self, chat_id: int):
        async with self.session.get(
            f'{telegram_context.common.BOT_BASE_URL.get()}unpinChatMessage',
            params={'chat_id': chat_id, 'message_id': telegram_context.common.MESSAGE_ID.get()}
        ) as response:
            return await functions.handle_request_exception(response)
    
    @async_fix
    async def copy_message(
            self,
            message_id: int,
            reply_markup: dict | None = None,
            from_chat_id: int = None,
            chat_id: int = None,
            protect_content: bool = False
    ):
        assert (chat_id and not from_chat_id) or (from_chat_id and not chat_id), \
            'You must use a chat_id or a from_chat_id !'
        base_param = {'message_id': message_id, 'protect_content': str(protect_content)}
        if reply_markup:
            base_param['reply_markup'] = json.dumps(reply_markup)
        async with self.session.get(
            f'{telegram_context.common.BOT_BASE_URL.get()}copyMessage',
            params={
                'from_chat_id': self.database.chat_id,
                'chat_id': chat_id,
                **base_param
            } if not from_chat_id else {'from_chat_id': from_chat_id, 'chat_id': self.database.chat_id, **base_param}
        ) as response:
            if response.status == 200:
                if (result := await response.json())['ok']:
                    return result['result']['message_id']
            elif response.status == 429:
                raise TooManyRequests((await response.json())['parameters']['retry_after'])
            return False

    @abstractmethod
    def _get_back_menu(self) -> dict:
        pass

    def __perform_back_callback(self, callback: str):
        if callback:
            return getattr(self, callback)()

    async def go_back(self):
        step = self._get_back_menu()
        self.database.menu = step['menu']
        self.database.back_menu = step.get('before')
        self.__perform_back_callback(step.get('callback'))
        async with TaskGroup() as tg:
            tg.create_task(self.database.asave())
            tg.create_task(self.send_message(step['message'], step.get('keyboard')))

    def menu_cleanup(self):
        self.__perform_back_callback(self._get_back_menu().get('callback'))
