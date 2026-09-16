from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.models import User
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.keyboards.order_kb import (
    get_checkout_keyboard,
    get_order_receipt_keyboard,
    get_user_orders_keyboard,
    get_order_detail_keyboard,
)
from app.keyboards.cart_kb import get_cart_keyboard
from app.keyboards.profile_kb import (
    get_delivery_confirmation_keyboard,
    get_checkout_data_edit_keyboard,
    get_cancel_edit_field_keyboard,
)
from app.utils.callback_factories import (
    CartActionCallback,
    OrderDetailCallback,
    CheckoutDataCallback,
)
from app.utils.formatters import (
    format_delivery_data_preview,
    format_checkout_preview,
    format_user_order_receipt,
    format_order_details,
)
from app.states.profile_states import ProfileSetupState, ProfileEditSingleState

router = Router(name="orders")

FIELD_NAMES = {
    "name": "имя и фамилию",
    "company": "название компании (или «Нет», если частное лицо)",
    "phone": "номер телефона",
    "city": "город",
    "address": "полный адрес доставки (улица, дом, офис/квартира)",
}


async def render_delivery_confirmation(
    event: Message | CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    text = format_delivery_data_preview(user)
    kb = get_delivery_confirmation_keyboard()

    if isinstance(event, CallbackQuery):
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartActionCallback.filter(F.action == "checkout"))
async def start_checkout_flow(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    cart_service = CartService(session)
    items, _, _, _ = await cart_service.get_cart_summary(user.id)
    if not items:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста. Невозможно оформить заказ.",
            reply_markup=get_cart_keyboard(has_items=False),
            parse_mode="HTML",
        )
        return

    # Check if profile is complete
    if not user.is_profile_complete():
        # Start Step 1 of Profile Setup
        await state.set_state(ProfileSetupState.waiting_for_full_name)
        text = (
            "📝 <b>Заполнение данных для доставки</b>\n\n"
            "Для оформления оптового заказа укажите данные получателя (заполняется 1 раз).\n\n"
            "Шаг 1/5: Введите ваше <b>имя и фамилию</b> (например, <code>Иван Иванов</code>):"
        )
        cancel_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=CartActionCallback(action="view").pack())]
            ]
        )
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    else:
        # Profile is already filled -> Show confirmation screen
        await render_delivery_confirmation(callback, user, session)


# ================= FSM Wizard: Profile Setup during Checkout =================

@router.message(ProfileSetupState.waiting_for_full_name)
async def fsm_full_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Имя слишком короткое. Введите ваше имя и фамилию:")
        return

    await state.update_data(saved_full_name=name)
    await state.set_state(ProfileSetupState.waiting_for_company)
    await message.answer(
        "Шаг 2/5: Введите <b>название вашей компании</b>.\n\n"
        "Если вы оформляете заказ как частное лицо, напишите «<b>Нет</b>»:",
        parse_mode="HTML",
    )


@router.message(ProfileSetupState.waiting_for_company)
async def fsm_company(message: Message, state: FSMContext) -> None:
    company = message.text.strip()
    await state.update_data(company_name=company)
    await state.set_state(ProfileSetupState.waiting_for_phone)
    await message.answer(
        "Шаг 3/5: Введите контактный <b>номер телефона</b> (например, <code>+7 777 123 45 67</code>):",
        parse_mode="HTML",
    )


@router.message(ProfileSetupState.waiting_for_phone)
async def fsm_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("⚠️ Введите корректный номер телефона:")
        return

    await state.update_data(phone=phone)
    await state.set_state(ProfileSetupState.waiting_for_city)
    await message.answer(
        "Шаг 4/5: Введите <b>город доставки</b> (например, <code>Астана</code>, <code>Алматы</code>, <code>Шымкент</code>):",
        parse_mode="HTML",
    )


@router.message(ProfileSetupState.waiting_for_city)
async def fsm_city(message: Message, state: FSMContext) -> None:
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("⚠️ Введите название города:")
        return

    await state.update_data(city=city)
    await state.set_state(ProfileSetupState.waiting_for_address)
    await message.answer(
        "Шаг 5/5: Введите <b>полный адрес доставки</b>:\n"
        "(Улица, дом, склад/офис/квартира):",
        parse_mode="HTML",
    )


@router.message(ProfileSetupState.waiting_for_address)
async def fsm_address(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    address = message.text.strip()
    if len(address) < 3:
        await message.answer("⚠️ Введите полный адрес доставки:")
        return

    data = await state.get_data()
    await state.clear()

    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=message.from_user.id)
    await user_repo.update_profile(
        user_id=user.id,
        full_name=data["saved_full_name"],
        company_name=data.get("company_name"),
        phone=data["phone"],
        city=data["city"],
        delivery_address=address,
    )

    await message.answer("✅ Данные сохранены.")
    updated_user = await user_repo.get_by_id(user.id)
    await render_delivery_confirmation(message, updated_user, session)


# ================= Checkout Confirmation Steps =================

@router.callback_query(CheckoutDataCallback.filter(F.action == "confirm_data"))
async def confirm_delivery_data_and_show_order(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)

    cart_service = CartService(session)
    items, total_amount, total_count, _ = await cart_service.get_cart_summary(user.id)

    if not items:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста.",
            reply_markup=get_cart_keyboard(has_items=False),
            parse_mode="HTML",
        )
        return

    text = format_checkout_preview(user, items, total_amount, total_count)
    kb = get_checkout_keyboard()
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CheckoutDataCallback.filter(F.action == "edit_data"))
async def edit_delivery_data_menu(
    callback: CallbackQuery,
) -> None:
    await callback.answer()
    text = "✏️ <b>Выберите поле, которое хотите изменить:</b>"
    kb = get_checkout_data_edit_keyboard()
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CheckoutDataCallback.filter(F.action == "edit_field"))
async def edit_single_field_in_checkout(
    callback: CallbackQuery,
    callback_data: CheckoutDataCallback,
    state: FSMContext,
) -> None:
    await callback.answer()
    field = callback_data.field or "address"
    await state.set_state(ProfileEditSingleState.waiting_for_field_value)
    await state.update_data(field=field, is_checkout=True)

    field_title = FIELD_NAMES.get(field, field)
    text = f"✏️ Введите новое значение: <b>{field_title}</b>"
    kb = get_cancel_edit_field_keyboard(is_checkout=True)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartActionCallback.filter(F.action == "confirm"))
async def confirm_final_order(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    order_service = OrderService(session)
    order = await order_service.create_order(user.id)

    if not order:
        await callback.message.edit_text(
            "⚠️ Ваша корзина пуста или произошла ошибка при оформлении.",
            reply_markup=get_cart_keyboard(has_items=False),
            parse_mode="HTML",
        )
        return

    # Load fresh order with items and user for notification
    full_order = await order_service.get_order_by_id(order.id)

    # 1. Send notification to Managers Telegram group
    if full_order:
        await NotificationService.send_order_to_managers(bot, full_order, user)

    # 2. Send receipt to client
    receipt_text = format_user_order_receipt(order)
    receipt_kb = get_order_receipt_keyboard()

    await callback.message.edit_text(
        receipt_text,
        reply_markup=receipt_kb,
        parse_mode="HTML",
    )


# ================= My Orders =================

@router.message(F.text == "📦 Мои заказы")
async def show_user_orders_msg(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await render_user_orders(message, session, page=1)


@router.callback_query(F.data.startswith("my_orders_page_"))
async def show_user_orders_cb(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()
    page_str = callback.data.replace("my_orders_page_", "")
    page = int(page_str) if page_str.isdigit() else 1
    await render_user_orders(callback, session, page=page)


async def render_user_orders(
    event: Message | CallbackQuery, session: AsyncSession, page: int = 1
) -> None:
    telegram_id = event.from_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=telegram_id)

    order_service = OrderService(session)
    orders, total_count, total_pages = await order_service.get_user_orders(
        user_id=user.id, page=page, page_size=5
    )

    if not orders:
        text = (
            "📦 <b>История заказов пуста</b>\n\n"
            "У вас пока нет оформленных заказов. Выберите товары в каталоге!"
        )
        kb = get_order_receipt_keyboard()
    else:
        text = (
            f"📦 <b>Ваши заказы</b> (Всего: {total_count})\n\n"
            "Нажмите на заказ, чтобы посмотреть детальный состав:"
        )
        kb = get_user_orders_keyboard(orders, page=page, total_pages=total_pages)

    if isinstance(event, CallbackQuery):
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(OrderDetailCallback.filter())
async def show_order_detail(
    callback: CallbackQuery,
    callback_data: OrderDetailCallback,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)

    order_service = OrderService(session)
    order = await order_service.get_order_by_id(callback_data.order_id)

    if not order or order.user_id != user.id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    text = format_order_details(order)
    kb = get_order_detail_keyboard(order.id, page=callback_data.page)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
