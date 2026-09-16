from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import CartItem
from app.utils.callback_factories import (
    CartActionCallback,
    CartItemCallback,
    CartItemQtyCallback,
)


def get_cart_keyboard(has_items: bool = True) -> InlineKeyboardMarkup:
    if not has_items:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛢 Открыть каталог", callback_data="open_catalog")],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Оформить заказ",
                    callback_data=CartActionCallback(action="checkout").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить товары",
                    callback_data="open_catalog",
                ),
                InlineKeyboardButton(
                    text="✏️ Изменить корзину",
                    callback_data=CartActionCallback(action="edit").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Очистить корзину",
                    callback_data=CartActionCallback(action="clear").pack(),
                )
            ],
        ]
    )


def get_cart_edit_list_keyboard(items: List[CartItem]) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        prod_name = item.product.name if item.product else "Товар"
        vol = f" ({item.product.volume})" if item.product and item.product.volume else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {prod_name}{vol} — {item.quantity} шт.",
                callback_data=CartItemCallback(product_id=item.product_id).pack(),
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад к корзине",
            callback_data=CartActionCallback(action="view").pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cart_item_edit_keyboard(product_id: int, quantity: int) -> InlineKeyboardMarkup:
    minus_qty = max(1, quantity - 1)
    plus_qty = quantity + 1

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=CartItemQtyCallback(product_id=product_id, quantity=minus_qty).pack(),
                ),
                InlineKeyboardButton(
                    text=f"🔢 {quantity} шт.",
                    callback_data="noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=CartItemQtyCallback(product_id=product_id, quantity=plus_qty).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить из корзины",
                    callback_data=CartItemQtyCallback(product_id=product_id, quantity=0).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к списку позиций",
                    callback_data=CartActionCallback(action="edit").pack(),
                ),
                InlineKeyboardButton(
                    text="🛒 В корзину",
                    callback_data=CartActionCallback(action="view").pack(),
                ),
            ],
        ]
    )
