from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.keyboards.profile_kb import (
    get_profile_keyboard,
    get_cancel_edit_field_keyboard,
)
from app.utils.callback_factories import ProfileCallback, CheckoutDataCallback, CartActionCallback
from app.utils.formatters import format_profile_text
from app.states.profile_states import ProfileEditSingleState

router = Router(name="profile")

FIELD_NAMES = {
    "name": "имя и фамилию",
    "company": "название компании (или «Нет», если частное лицо)",
    "phone": "номер телефона",
    "city": "город",
    "address": "полный адрес доставки (улица, дом, офис/квартира)",
}


@router.message(F.text == "👤 Мой профиль")
async def show_profile_msg(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    text = format_profile_text(user)
    kb = get_profile_keyboard()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ProfileCallback.filter(F.action == "view"))
async def show_profile_cb(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    text = format_profile_text(user)
    kb = get_profile_keyboard()
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ProfileCallback.filter(F.action == "edit_field"))
async def edit_profile_field_cb(
    callback: CallbackQuery,
    callback_data: ProfileCallback,
    state: FSMContext,
) -> None:
    await callback.answer()
    field = callback_data.field or "name"
    await state.set_state(ProfileEditSingleState.waiting_for_field_value)
    await state.update_data(field=field, is_checkout=False)

    field_title = FIELD_NAMES.get(field, field)
    text = f"✏️ Введите новое значение: <b>{field_title}</b>"
    kb = get_cancel_edit_field_keyboard(is_checkout=False)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(ProfileEditSingleState.waiting_for_field_value)
async def process_edit_field_value(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    val = message.text.strip()
    if not val:
        await message.answer("⚠️ Поле не может быть пустым. Пожалуйста, введите значение:")
        return

    data = await state.get_data()
    field = data.get("field", "name")
    is_checkout = data.get("is_checkout", False)

    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=message.from_user.id)
    await user_repo.update_field(user.id, field, val)
    await state.clear()

    # Re-fetch updated user
    updated_user = await user_repo.get_by_id(user.id)

    if is_checkout:
        from app.handlers.orders import render_delivery_confirmation
        await render_delivery_confirmation(message, updated_user, session)
    else:
        await message.answer("✅ Данные сохранены.")
        text = format_profile_text(updated_user)
        kb = get_profile_keyboard()
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
