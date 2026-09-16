from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Category, Product
from app.utils.callback_factories import (
    CategoryCallback,
    ProductCallback,
    ProductQuantityCallback,
    AddToCartCallback,
)


def get_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(
                text=f"🛢 {cat.name}",
                callback_data=CategoryCallback(category_id=cat.id, page=1).pack(),
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🛒 Корзина", callback_data="open_cart"),
        InlineKeyboardButton(text="🔎 Поиск", callback_data="start_search"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_products_keyboard(
    products: List[Product],
    category_id: int,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    buttons = []
    for prod in products:
        vol_str = f" ({prod.volume})" if prod.volume else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"🛢 {prod.name}{vol_str}",
                callback_data=ProductCallback(product_id=prod.id, category_id=category_id, page=page).pack(),
            )
        ])

    # Pagination row
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=CategoryCallback(category_id=category_id, page=page - 1).pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=CategoryCallback(category_id=category_id, page=page + 1).pack(),
            )
        )
    if len(nav_row) > 1:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔙 К категориям", callback_data="open_catalog"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="open_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_card_keyboard(
    product_id: int,
    quantity: int,
    category_id: int = 0,
    page: int = 1,
) -> InlineKeyboardMarkup:
    step = 1
    minus_qty = max(1, quantity - step)
    plus_qty = quantity + step

    buttons = [
        [
            InlineKeyboardButton(
                text="➖",
                callback_data=ProductQuantityCallback(
                    product_id=product_id, quantity=minus_qty, category_id=category_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text=f"🔢 {quantity} шт.",
                callback_data="manual_qty_prompt",
            ),
            InlineKeyboardButton(
                text="➕",
                callback_data=ProductQuantityCallback(
                    product_id=product_id, quantity=plus_qty, category_id=category_id, page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data=AddToCartCallback(
                    product_id=product_id, quantity=quantity, category_id=category_id, page=page
                ).pack(),
            )
        ],
    ]

    back_btn = (
        InlineKeyboardButton(
            text="🔙 Назад к списку",
            callback_data=CategoryCallback(category_id=category_id, page=page).pack(),
        )
        if category_id > 0
        else InlineKeyboardButton(text="🔙 В каталог", callback_data="open_catalog")
    )

    buttons.append([
        back_btn,
        InlineKeyboardButton(text="🛒 Корзина", callback_data="open_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
