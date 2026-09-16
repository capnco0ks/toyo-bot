from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.services.product_service import ProductService
from app.services.cart_service import CartService
from app.keyboards.catalog_kb import (
    get_categories_keyboard,
    get_products_keyboard,
    get_product_card_keyboard,
)
from app.utils.callback_factories import (
    CategoryCallback,
    ProductCallback,
    ProductQuantityCallback,
    AddToCartCallback,
)
from app.utils.formatters import format_product_card
from app.states.cart_states import ManualQuantityState

router = Router(name="catalog")


@router.message(F.text == "🛢 Каталог")
@router.callback_query(F.data == "open_catalog")
async def show_catalog(event: Message | CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    product_service = ProductService(session)
    categories = await product_service.get_active_categories()

    text = "🛢 <b>Каталог продукции TOYO</b>\n\nВыберите категорию масел:"
    kb = get_categories_keyboard(categories)

    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(CategoryCallback.filter())
async def show_category_products(
    callback: CallbackQuery,
    callback_data: CategoryCallback,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.answer()
    product_service = ProductService(session)
    category = await product_service.get_category_by_id(callback_data.category_id)
    if not category:
        await callback.message.answer("Категория не найдена.")
        return

    products, total_count, total_pages = await product_service.get_products_by_category(
        category_id=category.id,
        only_active=True,
        page=callback_data.page,
        page_size=6,
    )

    text = (
        f"📁 <b>{category.name}</b>\n"
        f"Всего товаров в категории: <b>{total_count}</b>\n\n"
        "Выберите товар для просмотра характеристик и добавления в заказ:"
    )
    kb = get_products_keyboard(
        products=products,
        category_id=category.id,
        page=callback_data.page,
        total_pages=total_pages,
    )

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ProductCallback.filter())
async def show_product_card(
    callback: CallbackQuery,
    callback_data: ProductCallback,
    session: AsyncSession,
) -> None:
    await callback.answer()
    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    if not product:
        await callback.message.answer("Товар не найден или был удалён.")
        return

    quantity = product.min_order_quantity or 1
    text = format_product_card(product, quantity=quantity)
    kb = get_product_card_keyboard(
        product_id=product.id,
        quantity=quantity,
        category_id=callback_data.category_id,
        page=callback_data.page,
    )

    if product.photo_file_id:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=product.photo_file_id,
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
    else:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ProductQuantityCallback.filter())
async def change_product_quantity(
    callback: CallbackQuery,
    callback_data: ProductQuantityCallback,
    session: AsyncSession,
) -> None:
    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    quantity = max(1, callback_data.quantity)
    text = format_product_card(product, quantity=quantity)
    kb = get_product_card_keyboard(
        product_id=product.id,
        quantity=quantity,
        category_id=callback_data.category_id,
        page=callback_data.page,
    )

    await callback.answer()
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "manual_qty_prompt")
async def prompt_manual_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ManualQuantityState.waiting_for_quantity)
    await callback.message.answer(
        "✏️ Введите необходимое количество (целое число от 1 до 10000):"
    )


@router.message(ManualQuantityState.waiting_for_quantity)
async def process_manual_quantity(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer("⚠️ Пожалуйста, введите положительное целое число (например, 10):")
        return

    qty = int(text)
    if qty > 50000:
        await message.answer("⚠️ Количество слишком большое. Введите значение до 50 000:")
        return

    await state.clear()
    await message.answer(
        f"Количество установлено: <b>{qty} шт.</b>\n"
        "Вы можете выбрать товар в каталоге или открыть корзину.",
        parse_mode="HTML",
    )


@router.callback_query(AddToCartCallback.filter())
async def add_to_cart_handler(
    callback: CallbackQuery,
    callback_data: AddToCartCallback,
    session: AsyncSession,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    cart_service = CartService(session)
    await cart_service.add_item(
        user_id=user.id,
        product_id=product.id,
        quantity=callback_data.quantity,
    )

    await callback.answer(
        f"✅ Добавлено в корзину: {product.name} ({callback_data.quantity} шт.)",
        show_alert=False,
    )
