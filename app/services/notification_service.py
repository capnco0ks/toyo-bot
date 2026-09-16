import logging
from typing import Optional
from aiogram import Bot
from app.config import settings
from app.database.models import Order, User
from app.utils.formatters import (
    format_manager_order_notification,
    format_currency,
    format_status,
)
from app.keyboards.order_kb import get_manager_order_keyboard

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def send_order_to_managers(bot: Bot, order: Order, user: User) -> Optional[int]:
        """
        Sends formatted order card to ORDER_CHAT_ID with inline buttons.
        Returns message_id if sent successfully.
        """
        if not settings.ORDER_CHAT_ID:
            logger.warning("ORDER_CHAT_ID is not set in .env. Skipping manager notification.")
            return None

        text = format_manager_order_notification(order, user)
        kb = get_manager_order_keyboard(order.id)

        try:
            msg = await bot.send_message(
                chat_id=settings.ORDER_CHAT_ID,
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Failed to send order notification to ORDER_CHAT_ID {settings.ORDER_CHAT_ID}: {e}")
            return None

    @staticmethod
    async def notify_user_status_update(bot: Bot, user_telegram_id: int, order: Order) -> bool:
        """
        Notifies client about status change of their order.
        """
        text = (
            f"🔔 <b>Обновление статуса заказа №{order.id}</b>\n\n"
            f"Новый статус: <b>{format_status(order.status)}</b>\n"
            f"Сумма: <b>{format_currency(order.total_amount)}</b>"
        )
        try:
            await bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.warning(f"Could not notify user {user_telegram_id} of status update: {e}")
            return False
