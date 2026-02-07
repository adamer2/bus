from contextvars import ContextVar

BOT_BASE_URL = ContextVar('BOT_BASE_URL')
HTTP_SESSION = ContextVar('HTTP_SESSION')
USER_CHAT_ID = ContextVar('USER_CHAT_ID')
USER = ContextVar('USER')
CHAT_ID = ContextVar('CHAT_ID')
MESSAGE_ID = ContextVar('MESSAGE_ID')
