import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Unhandled exception while processing update: {e}")
            error_msg = "⚠️ Произошла ошибка. Попробуйте ещё раз или обратитесь к менеджеру."
            if isinstance(event, Message):
                try:
                    await event.answer(error_msg)
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(error_msg, show_alert=True)
                except Exception:
                    pass
            return None
