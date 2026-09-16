from datetime import datetime
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.utils.callback_factories import ManagerOrderActionCallback
from app.keyboards.order_kb import get_manager_order_accepted_keyboard
from app.utils.formatters import (
    format_manager_order_notification,
    format_status,
)

router = Router(name="manager_orders")


@router.callback_query(ManagerOrderActionCallback.filter())
async def handle_manager_order_action(
    callback: CallbackQuery,
    callback_data: ManagerOrderActionCallback,
    session: AsyncSession,
    bot: Bot,
) -> None:
    order_service = OrderService(session)
    order = await order_service.get_order_by_id(callback_data.order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    manager_name = callback.from_user.full_name
    manager_tag = f"@{callback.from_user.username}" if callback.from_user.username else manager_name
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    if callback_data.action == "accept":
        await order_service.update_order_status(order.id, "accepted")
        await callback.answer("✅ Заказ принят в работу")
        status_info = f"✅ <b>ПРИНЯТ В РАБОТУ</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        new_kb = get_manager_order_accepted_keyboard(order.id)
        await callback.message.edit_text(new_text, reply_markup=new_kb, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)

    elif callback_data.action == "reject":
        await order_service.update_order_status(order.id, "rejected")
        await callback.answer("❌ Заказ отклонён")
        status_info = f"❌ <b>ОТКЛОНЁН</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)

    elif callback_data.action == "complete":
        await order_service.update_order_status(order.id, "completed")
        await callback.answer("🏁 Заказ завершён")
        status_info = f"🏁 <b>ЗАВЕРШЁН (ОТГРУЖЕН)</b>\n👤 Менеджер: {manager_tag}\n🕐 {now_str}"
        new_text = format_manager_order_notification(order, order.user, manager_info=status_info)
        await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")

        # Notify client
        if order.user:
            await NotificationService.notify_user_status_update(bot, order.user.telegram_id, order)
