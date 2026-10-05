from datetime import datetime, timezone
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.utils.callback_factories import ManagerOrderActionCallback
from app.keyboards.order_kb import get_manager_order_accepted_keyboard
from app.utils.formatters import (
    format_manager_order_notification,
    format_date,
)

router = Router(name="manager_orders")


def is_authorized_manager(user_id: int) -> bool:
    """
    If MANAGER_IDS is specified in settings, only listed managers and admins
    can process orders. If MANAGER_IDS is empty, any member of ORDER_CHAT_ID may process.
    """
    if settings.MANAGER_IDS:
        return user_id in settings.MANAGER_IDS or user_id in settings.ADMIN_IDS
    return True


@router.callback_query(ManagerOrderActionCallback.filter())
async def handle_manager_order_action(
    callback: CallbackQuery,
    callback_data: ManagerOrderActionCallback,
    session: AsyncSession,
    bot: Bot,
) -> None:
    user_id = callback.from_user.id
    if not is_authorized_manager(user_id):
        await callback.answer("⛔ У вас нет прав для управления заказами.", show_alert=True)
        return

    order_service = OrderService(session)
    order = await order_service.get_order_by_id(callback_data.order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    manager_name = callback.from_user.full_name
    manager_tag = f"@{callback.from_user.username}" if callback.from_user.username else manager_name
    now_str = format_date(datetime.now(timezone.utc))

    if callback_data.action == "accept":
        if order.status in ["accepted", "completed", "rejected"]:
            by = f" ({order.accepted_by_name})" if order.accepted_by_name else ""
            await callback.answer(f"⚠️ Этот заказ уже обработан{by}.", show_alert=True)
            return

        await order_service.update_order_status(
            order.id,
            "accepted",
            accepted_by_id=user_id,
            accepted_by_name=manager_tag,
        )
        await callback.answer("✅ Заказ принят в работу")
        status_info = f"✅ <b>ПРИНЯТ В РАБОТУ</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        new_kb = get_manager_order_accepted_keyboard(order.id)
        await callback.message.edit_text(new_text, reply_markup=new_kb, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)

    elif callback_data.action == "reject":
        if order.status in ["completed", "rejected"]:
            await callback.answer(f"⚠️ Заказ уже находится в статусе «{order.status}».", show_alert=True)
            return

        # If order was already accepted by a specific manager, only they or an admin can reject it
        if order.accepted_by_id and user_id != order.accepted_by_id and user_id not in settings.ADMIN_IDS:
            owner = order.accepted_by_name or "другой менеджер"
            await callback.answer(
                f"⛔ Этот заказ ведёт {owner}.\nОтклонить его может только он или администратор.",
                show_alert=True,
            )
            return

        await order_service.update_order_status(
            order.id,
            "rejected",
            accepted_by_id=user_id,
            accepted_by_name=manager_tag,
        )
        await callback.answer("❌ Заказ отклонён")
        status_info = f"❌ <b>ОТКЛОНЁН</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)

    elif callback_data.action == "complete":
        if order.status == "completed":
            await callback.answer("⚠️ Заказ уже был отмечен как завершённый!", show_alert=True)
            return

        # Only the manager who accepted the order (or an admin) may complete it
        if order.accepted_by_id and user_id != order.accepted_by_id and user_id not in settings.ADMIN_IDS:
            owner = order.accepted_by_name or "другой менеджер"
            await callback.answer(
                f"⛔ Этот заказ ведёт {owner}!\nЗавершить его может только он или администратор.",
                show_alert=True,
            )
            return

        await order_service.update_order_status(
            order.id,
            "completed",
            accepted_by_id=user_id,
            accepted_by_name=manager_tag,
        )
        await callback.answer("🏁 Заказ завершён")
        status_info = f"🏁 <b>ЗАВЕРШЁН (ОТГРУЖЕН)</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)
