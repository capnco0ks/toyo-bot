from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Order
from app.utils.callback_factories import (
    OrderDetailCallback,
    ManagerOrderActionCallback,
    CartActionCallback,
    CheckoutDataCallback,
)
from app.utils.formatters import format_currency, format_status, format_date


def get_checkout_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить заказ",
                    callback_data=CartActionCallback(action="confirm").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить данные",
                    callback_data=CheckoutDataCallback(action="edit_data").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Изменить корзину",
                    callback_data=CartActionCallback(action="view").pack(),
                )
            ],
        ]
    )


def get_order_receipt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders_page_1"),
                InlineKeyboardButton(text="🛢 Каталог", callback_data="open_catalog"),
            ]
        ]
    )


def get_manager_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=ManagerOrderActionCallback(order_id=order_id, action="accept").pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=ManagerOrderActionCallback(order_id=order_id, action="reject").pack(),
                ),
            ]
        ]
    )


def get_manager_order_accepted_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏁 Отметить завершённым",
                    callback_data=ManagerOrderActionCallback(order_id=order_id, action="complete").pack(),
                )
            ]
        ]
    )


def get_user_orders_keyboard(
    orders: List[Order], page: int, total_pages: int
) -> InlineKeyboardMarkup:
    buttons = []
    for order in orders:
        dt_str = format_date(order.created_at, include_time=False)
        st_icon = "🆕" if order.status == "new" else ("✅" if order.status == "accepted" else ("❌" if order.status == "rejected" else "🏁"))
        buttons.append([
            InlineKeyboardButton(
                text=f"{st_icon} №{order.id} | {format_currency(order.total_amount)} | {dt_str}",
                callback_data=OrderDetailCallback(order_id=order.id, page=page).pack(),
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"my_orders_page_{page - 1}",
            )
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"my_orders_page_{page + 1}",
            )
        )
    if len(nav_row) > 1:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🛢 В каталог", callback_data="open_catalog"),
        InlineKeyboardButton(text="🛒 В корзину", callback_data="open_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_detail_keyboard(order_id: int, page: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Назад к списку заказов",
                    callback_data=f"my_orders_page_{page}",
                )
            ],
            [
                InlineKeyboardButton(text="🛢 В каталог", callback_data="open_catalog"),
                InlineKeyboardButton(text="🛒 В корзину", callback_data="open_cart"),
            ],
        ]
    )
