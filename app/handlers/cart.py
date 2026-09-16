from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.services.cart_service import CartService
from app.services.product_service import ProductService
from app.keyboards.cart_kb import (
    get_cart_keyboard,
    get_cart_edit_list_keyboard,
    get_cart_item_edit_keyboard,
)
from app.utils.callback_factories import (
    CartActionCallback,
    CartItemCallback,
    CartItemQtyCallback,
)
from app.utils.formatters import format_cart_text, format_currency

router = Router(name="cart")


@router.message(F.text == "🛒 Корзина")
@router.callback_query(F.data == "open_cart")
@router.callback_query(CartActionCallback.filter(F.action == "view"))
async def show_cart(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    telegram_id = event.from_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=telegram_id,
        username=event.from_user.username,
        first_name=event.from_user.first_name,
        last_name=event.from_user.last_name,
    )

    cart_service = CartService(session)
    items, total_amount, total_count, total_positions = await cart_service.get_cart_summary(user.id)

    text = format_cart_text(
        items=items,
        total_amount=total_amount,
        total_count=total_count,
        total_positions=total_positions,
    )
    kb = get_cart_keyboard(has_items=bool(items))

    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartActionCallback.filter(F.action == "edit"))
async def edit_cart_list(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    cart_service = CartService(session)
    items, _, _, _ = await cart_service.get_cart_summary(user.id)

    if not items:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста.",
            reply_markup=get_cart_keyboard(has_items=False),
            parse_mode="HTML",
        )
        return

    text = "✏️ <b>Редактирование корзины</b>\n\nВыберите позицию для изменения количества или удаления:"
    kb = get_cart_edit_list_keyboard(items)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartItemCallback.filter())
async def edit_cart_single_item(
    callback: CallbackQuery,
    callback_data: CartItemCallback,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)

    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    cart_service = CartService(session)
    items = (await cart_service.repo.get_user_cart(user.id))
    current_item = next((i for i in items if i.product_id == product.id), None)
    qty = current_item.quantity if current_item else 1

    vol = f" ({product.volume})" if product.volume else ""
    text = (
        f"✏️ <b>{product.name}{vol}</b>\n\n"
        f"Цена за ед.: <b>{format_currency(product.price)}</b>\n"
        f"Количество в корзине: <b>{qty} шт.</b>\n"
        f"Сумма: <b>{format_currency(product.price * qty)}</b>\n\n"
        "Используйте кнопки для изменения количества или удаления:"
    )
    kb = get_cart_item_edit_keyboard(product.id, qty)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartItemQtyCallback.filter())
async def change_cart_item_qty(
    callback: CallbackQuery,
    callback_data: CartItemQtyCallback,
    session: AsyncSession,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    cart_service = CartService(session)

    if callback_data.quantity <= 0:
        await cart_service.remove_item(user.id, callback_data.product_id)
        await callback.answer("🗑 Товар удален из корзины")
        # Return to cart overview
        items, total_amount, total_count, total_positions = await cart_service.get_cart_summary(user.id)
        text = format_cart_text(items, total_amount, total_count, total_positions)
        kb = get_cart_keyboard(has_items=bool(items))
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    await cart_service.update_quantity(user.id, callback_data.product_id, callback_data.quantity)
    await callback.answer()

    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    vol = f" ({product.volume})" if product and product.volume else ""
    price = product.price if product else 0
    qty = callback_data.quantity

    text = (
        f"✏️ <b>{product.name if product else 'Товар'}{vol}</b>\n\n"
        f"Цена за ед.: <b>{format_currency(price)}</b>\n"
        f"Количество в корзине: <b>{qty} шт.</b>\n"
        f"Сумма: <b>{format_currency(price * qty)}</b>\n\n"
        "Используйте кнопки для изменения количества или удаления:"
    )
    kb = get_cart_item_edit_keyboard(callback_data.product_id, qty)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CartActionCallback.filter(F.action == "clear"))
async def clear_cart_handler(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    cart_service = CartService(session)
    await cart_service.clear_cart(user.id)

    await callback.answer("🗑 Корзина очищена")
    await callback.message.edit_text(
        "🛒 <b>Ваша корзина пуста.</b>\n\nПерейдите в каталог, чтобы выбрать товары.",
        reply_markup=get_cart_keyboard(has_items=False),
        parse_mode="HTML",
    )
