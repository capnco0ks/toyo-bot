from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def get_main_reply_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    is_admin = user_id in settings.ADMIN_IDS
    buttons = [
        [KeyboardButton(text="🛢 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="🔎 Поиск"), KeyboardButton(text="📞 Связаться с менеджером")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        is_persistent=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_contact_manager_keyboard() -> InlineKeyboardMarkup:
    manager_url = f"https://t.me/{settings.MANAGER_USERNAME.lstrip('@')}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать менеджеру", url=manager_url)],
            [InlineKeyboardButton(text="🛢 Открыть каталог", callback_data="open_catalog")],
        ]
    )
