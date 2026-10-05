from datetime import datetime, timedelta
from typing import List, Optional
from app.config import settings
from app.database.models import Product, Order, OrderItem, User


def format_currency(amount: float | int) -> str:
    """
    Formats number as currency string with spaces: 190000 -> 190 000 ₸
    """
    int_amount = int(round(amount))
    formatted = f"{int_amount:,}".replace(",", " ")
    return f"{formatted} ₸"


def format_status(status: str) -> str:
    status_map = {
        "new": "🆕 НОВЫЙ",
        "accepted": "✅ ПРИНЯТ",
        "rejected": "❌ ОТКЛОНЁН",
        "completed": "🏁 ЗАВЕРШЁН",
        "processing": "⏳ В ОБРАБОТКЕ",
        "cancelled": "🚫 ОТМЕНЁН",
    }
    return status_map.get(status.lower(), status.upper())


def format_date(dt: datetime, include_time: bool = True) -> str:
    if not dt:
        return ""
    local_dt = dt
    tz_offset = getattr(settings, "TZ_OFFSET_HOURS", 5)
    if tz_offset:
        local_dt = dt + timedelta(hours=tz_offset)
    if include_time:
        return local_dt.strftime("%d.%m.%Y %H:%M")
    return local_dt.strftime("%d.%m.%Y")


def format_product_card(product: Product, quantity: int = 1) -> str:
    lines = [f"🛢 <b>{product.name}</b>\n"]
    if product.category:
        lines.append(f"📁 Категория: <b>{product.category.name}</b>")
    if product.viscosity:
        lines.append(f"🧪 Вязкость: <b>{product.viscosity}</b>")
    if product.volume:
        lines.append(f"🧴 Объём: <b>{product.volume}</b>")
    if product.package:
        lines.append(f"📦 Фасовка / Тара: <b>{product.package}</b>")
    if product.article:
        lines.append(f"🏷 Артикул: <code>{product.article}</code>")
    if product.description:
        lines.append(f"\n📝 {product.description}")

    lines.append(f"\n💰 Цена: <b>{format_currency(product.price)}</b>")

    if product.min_order_quantity > 1:
        lines.append(f"⚠️ Мин. партия: <b>{product.min_order_quantity} шт.</b>")

    item_total = product.price * quantity
    lines.append(f"\n🔢 Выбрано: <b>{quantity} шт.</b>")
    if quantity > 1:
        lines.append(f"💵 Сумма: <b>{format_currency(item_total)}</b>")

    return "\n".join(lines)


def format_cart_text(items: list, total_amount: float, total_count: int, total_positions: int) -> str:
    if not items:
        return "🛒 <b>Ваша корзина пуста.</b>\n\nПерейдите в каталог, чтобы выбрать товары."

    lines = ["🛒 <b>Ваша корзина</b>\n"]
    for i, item in enumerate(items, 1):
        prod = item.product
        prod_name = prod.full_title if prod else "Товар"
        price = prod.price if prod else 0
        subtotal = price * item.quantity
        lines.append(
            f"<b>{i}. {prod_name}</b>\n"
            f"   {item.quantity} шт. × {format_currency(price)} = <b>{format_currency(subtotal)}</b>\n"
        )

    lines.append("─────────────────────")
    lines.append(f"📦 Позиций: <b>{total_positions}</b>")
    lines.append(f"🔢 Количество: <b>{total_count} шт.</b>\n")
    lines.append(f"💰 <b>ИТОГО: {format_currency(total_amount)}</b>")
    return "\n".join(lines)


def format_profile_text(user: User) -> str:
    company = user.company_name if user.company_name else "<i>(частное лицо)</i>"
    lines = [
        "👤 <b>Ваш профиль клиента:</b>\n",
        f"👤 <b>Имя и фамилия:</b> {user.saved_full_name or '<i>не указано</i>'}",
        f"🏢 <b>Компания:</b> {company}",
        f"📱 <b>Телефон:</b> {user.phone or '<i>не указан</i>'}",
        f"📍 <b>Город:</b> {user.city or '<i>не указан</i>'}",
        f"🏠 <b>Адрес доставки:</b> {user.delivery_address or '<i>не указан</i>'}",
    ]
    return "\n".join(lines)


def format_delivery_data_preview(user: User) -> str:
    company = user.company_name if user.company_name else "Частное лицо"
    lines = [
        "📋 <b>Данные для заказа:</b>\n",
        f"👤 <b>Имя:</b> {user.saved_full_name or user.display_name}",
        f"🏢 <b>Компания:</b> {company}",
        f"📱 <b>Телефон:</b> {user.phone}",
        f"📍 <b>Город:</b> {user.city}",
        f"🏠 <b>Адрес:</b> {user.delivery_address}\n",
        "Проверьте данные перед оформлением."
    ]
    return "\n".join(lines)


def format_checkout_preview(
    user: User, items: list, total_amount: float, total_count: int
) -> str:
    company = user.company_name if user.company_name else "Частное лицо"
    lines = [
        "📦 <b>ПРОВЕРКА ЗАКАЗА</b>\n",
        f"👤 <b>Клиент:</b> {user.saved_full_name or user.display_name}",
        f"🏢 <b>Компания:</b> {company}",
        f"📱 <b>Телефон:</b> {user.phone}",
        f"🚚 <b>Доставка:</b> {user.city}, {user.delivery_address}\n",
        "━━━━━━━━━━━━━━\n",
        "<b>ТОВАРЫ:</b>\n",
    ]
    for i, item in enumerate(items, 1):
        prod = item.product
        prod_name = prod.full_title if prod else "Товар"
        price = prod.price if prod else 0
        subtotal = price * item.quantity
        lines.append(
            f"{i}. <b>{prod_name}</b>\n"
            f"   {item.quantity} шт. × {format_currency(price)} = <b>{format_currency(subtotal)}</b>\n"
        )

    lines.append("━━━━━━━━━━━━━━\n")
    lines.append(f"🔢 Количество: <b>{total_count} шт.</b>")
    lines.append(f"💰 <b>ИТОГО: {format_currency(total_amount)}</b>")
    return "\n".join(lines)


def format_manager_order_notification(
    order: Order,
    user: User,
    manager_info: Optional[str] = None
) -> str:
    cust_name = order.customer_name or (user.saved_full_name or user.display_name)
    company = order.company_name if order.company_name else (user.company_name if user.company_name else "Частное лицо")
    phone = order.phone or user.phone or "не указан"
    city = order.city or user.city or ""
    address = order.delivery_address or user.delivery_address or ""

    lines = [
        f"🛒 <b>НОВЫЙ ОПТОВЫЙ ЗАКАЗ</b>\n",
        f"<b>№{order.id}</b>\n",
        f"👤 <b>Клиент:</b> {cust_name}",
        f"🏢 <b>Компания:</b> {company}",
        f"📱 <b>Телефон:</b> <code>{phone}</code>",
        f"📍 <b>Город:</b> {city}",
        f"🏠 <b>Адрес доставки:</b> {address}",
        f"💬 <b>Telegram:</b> @{user.username}" if user.username else "💬 <b>Telegram:</b> <i>(скрыт/без юзернейма)</i>",
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n",
        "━━━━━━━━━━━━━━\n",
        "📦 <b>ТОВАРЫ:</b>\n",
    ]

    total_qty = 0
    for i, item in enumerate(order.items, 1):
        total_qty += item.quantity
        lines.append(
            f"{i}. <b>{item.product_name}</b>\n"
            f"   {item.quantity} шт. × {format_currency(item.price_at_purchase)}\n"
            f"   = <b>{format_currency(item.total)}</b>\n"
        )

    lines.append("━━━━━━━━━━━━━━\n")
    lines.append(f"🔢 Всего: <b>{total_qty} шт.</b>")
    lines.append(f"💰 <b>ИТОГО: {format_currency(order.total_amount)}</b>\n")
    lines.append(f"🕐 <b>Дата:</b> {format_date(order.created_at)}")
    lines.append(f"📌 <b>Статус:</b> {format_status(order.status)}")

    if manager_info:
        lines.append(f"\n{manager_info}")

    return "\n".join(lines)


def format_user_order_receipt(order: Order) -> str:
    lines = [
        f"✅ <b>Заказ №{order.id} успешно оформлен!</b>\n",
        f"💰 <b>Сумма заказа:</b> {format_currency(order.total_amount)}\n",
        "Менеджер получил ваш заказ и свяжется с вами в ближайшее время для согласования деталей и выставления счёта.\n",
        "Вы можете отслеживать статус заказа в разделе <b>«📦 Мои заказы»</b>.",
    ]
    return "\n".join(lines)


def format_order_details(order: Order) -> str:
    cust_name = order.customer_name or "Клиент"
    company = order.company_name if order.company_name else "Частное лицо"
    phone = order.phone or "не указан"
    city = order.city or ""
    address = order.delivery_address or ""

    lines = [
        f"📦 <b>Заказ №{order.id}</b>",
        f"📅 Дата: <b>{format_date(order.created_at)}</b>",
        f"📌 Статус: <b>{format_status(order.status)}</b>\n",
        f"👤 Клиент: <b>{cust_name}</b>",
        f"🏢 Компания: <b>{company}</b>",
        f"📱 Телефон: <b>{phone}</b>",
        f"🏠 Доставка: <b>{city}, {address}</b>\n",
        "━━━━━━━━━━━━━━",
        "<b>Состав заказа:</b>\n",
    ]
    total_qty = 0
    for i, item in enumerate(order.items, 1):
        total_qty += item.quantity
        lines.append(
            f"{i}. <b>{item.product_name}</b>\n"
            f"   {item.quantity} шт. × {format_currency(item.price_at_purchase)} = {format_currency(item.total)}"
        )

    lines.append("\n━━━━━━━━━━━━━━")
    lines.append(f"Количество: <b>{total_qty} шт.</b>")
    lines.append(f"💰 <b>ИТОГО: {format_currency(order.total_amount)}</b>")
    return "\n".join(lines)
