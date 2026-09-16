from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Category, Product
from app.utils.callback_factories import (
    AdminMenuCallback,
    AdminCategoryCallback,
    AdminProductCallback,
)
from app.utils.formatters import format_currency


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Товары",
                    callback_data=AdminMenuCallback(menu="products").pack(),
                ),
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data=AdminMenuCallback(menu="add_product").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Изменить цену",
                    callback_data=AdminMenuCallback(menu="edit_price").pack(),
                ),
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data=AdminMenuCallback(menu="stats").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="open_main_menu",
                )
            ],
        ]
    )


def get_admin_categories_keyboard(
    categories: List[Category], action: str = "view"
) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=AdminCategoryCallback(
                    category_id=cat.id, action=action, page=1
                ).pack(),
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🔙 В админ-панель",
            callback_data=AdminMenuCallback(menu="main").pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_products_keyboard(
    products: List[Product],
    category_id: int,
    action: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    buttons = []
    for prod in products:
        status_icon = "🟢" if prod.is_active else "🔴"
        vol = f" ({prod.volume})" if prod.volume else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {prod.name}{vol} — {format_currency(prod.price)}",
                callback_data=AdminProductCallback(
                    product_id=prod.id, action=action, category_id=category_id, page=page
                ).pack(),
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCategoryCallback(
                    category_id=category_id, action=action, page=page - 1
                ).pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=AdminCategoryCallback(
                    category_id=category_id, action=action, page=page + 1
                ).pack(),
            )
        )
    if len(nav_row) > 1:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(
            text="🔙 К категориям",
            callback_data=AdminMenuCallback(menu="products" if action == "view" else "edit_price").pack(),
        ),
        InlineKeyboardButton(
            text="⚙️ Админка",
            callback_data=AdminMenuCallback(menu="main").pack(),
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_product_detail_keyboard(
    product: Product, category_id: int, page: int
) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Отключить товар" if product.is_active else "🟢 Включить товар"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Изменить цену",
                    callback_data=AdminProductCallback(
                        product_id=product.id, action="edit_price", category_id=category_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=AdminProductCallback(
                        product_id=product.id, action="toggle", category_id=category_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить товар",
                    callback_data=AdminProductCallback(
                        product_id=product.id, action="delete", category_id=category_id, page=page
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к списку",
                    callback_data=AdminCategoryCallback(
                        category_id=category_id, action="view", page=page
                    ).pack(),
                )
            ],
        ]
    )


def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=AdminMenuCallback(menu="main").pack(),
                )
            ]
        ]
    )
