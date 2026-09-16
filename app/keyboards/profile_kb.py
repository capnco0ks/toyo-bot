from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.callback_factories import ProfileCallback, CheckoutDataCallback, CartActionCallback


def get_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить имя",
                    callback_data=ProfileCallback(action="edit_field", field="name").pack(),
                ),
                InlineKeyboardButton(
                    text="✏️ Изменить компанию",
                    callback_data=ProfileCallback(action="edit_field", field="company").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить телефон",
                    callback_data=ProfileCallback(action="edit_field", field="phone").pack(),
                ),
                InlineKeyboardButton(
                    text="✏️ Изменить город",
                    callback_data=ProfileCallback(action="edit_field", field="city").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить адрес",
                    callback_data=ProfileCallback(action="edit_field", field="address").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="open_main_menu",
                )
            ],
        ]
    )


def get_delivery_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Всё верно",
                    callback_data=CheckoutDataCallback(action="confirm_data").pack(),
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
                    text="🛒 Вернуться в корзину",
                    callback_data=CartActionCallback(action="view").pack(),
                )
            ],
        ]
    )


def get_checkout_data_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Имя",
                    callback_data=CheckoutDataCallback(action="edit_field", field="name").pack(),
                ),
                InlineKeyboardButton(
                    text="✏️ Компания",
                    callback_data=CheckoutDataCallback(action="edit_field", field="company").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Телефон",
                    callback_data=CheckoutDataCallback(action="edit_field", field="phone").pack(),
                ),
                InlineKeyboardButton(
                    text="✏️ Город",
                    callback_data=CheckoutDataCallback(action="edit_field", field="city").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Адрес",
                    callback_data=CheckoutDataCallback(action="edit_field", field="address").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к проверке",
                    callback_data=CartActionCallback(action="checkout").pack(),
                )
            ],
        ]
    )


def get_cancel_edit_field_keyboard(is_checkout: bool = False) -> InlineKeyboardMarkup:
    back_data = (
        CheckoutDataCallback(action="edit_data").pack()
        if is_checkout
        else ProfileCallback(action="view").pack()
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=back_data)]
        ]
    )
