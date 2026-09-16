from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from app.database.repositories.category_repo import CategoryRepository
from app.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_admin_categories_keyboard,
    get_admin_products_keyboard,
    get_admin_product_detail_keyboard,
    get_admin_cancel_keyboard,
)
from app.utils.callback_factories import (
    AdminMenuCallback,
    AdminCategoryCallback,
    AdminProductCallback,
)
from app.utils.formatters import format_currency, format_product_card
from app.states.admin_states import EditPriceState, AddProductState

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(F.text == "⚙️ Админ-панель")
@router.message(Command("admin"))
async def admin_panel_entry(
    event: Message | CallbackQuery,
    state: FSMContext,
) -> None:
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Доступ ограничен. Только для администраторов.", show_alert=True)
        else:
            await event.answer("⛔ У вас нет прав доступа к панели администратора.")
        return

    await state.clear()
    text = (
        "⚙️ <b>Панель администратора TOYO</b>\n\n"
        "Выберите необходимое действие:"
    )
    kb = get_admin_main_keyboard()

    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminMenuCallback.filter())
async def admin_menu_handler(
    callback: CallbackQuery,
    callback_data: AdminMenuCallback,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.clear()
    product_service = ProductService(session)

    if callback_data.menu == "main":
        text = "⚙️ <b>Панель администратора TOYO</b>\n\nВыберите необходимое действие:"
        kb = get_admin_main_keyboard()
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    elif callback_data.menu == "products":
        categories = await product_service.get_all_categories()
        text = "📦 <b>Управление товарами</b>\n\nВыберите категорию для просмотра и редактирования:"
        kb = get_admin_categories_keyboard(categories, action="view")
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    elif callback_data.menu == "edit_price":
        categories = await product_service.get_all_categories()
        text = "💰 <b>Быстрое изменение цен</b>\n\nВыберите категорию товара:"
        kb = get_admin_categories_keyboard(categories, action="edit_price_in")
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    elif callback_data.menu == "add_product":
        categories = await product_service.get_all_categories()
        if not categories:
            await callback.answer("Сначала создайте хотя бы одну категорию", show_alert=True)
            return

        await state.set_state(AddProductState.waiting_for_category)
        text = "➕ <b>Добавление нового товара</b>\n\nШаг 1: Выберите категорию:"
        buttons = []
        for cat in categories:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📁 {cat.name}",
                    callback_data=f"adm_add_cat_{cat.id}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=AdminMenuCallback(menu="main").pack(),
            )
        ])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        await callback.answer()

    elif callback_data.menu == "stats":
        order_service = OrderService(session)
        stats = await order_service.get_stats()
        text = (
            "📊 <b>Статистика системы:</b>\n\n"
            f"🛒 Всего заказов: <b>{stats['total_orders']}</b>\n"
            f"🆕 Новых заказов: <b>{stats['new_orders']}</b>\n"
            f"✅ Принятых заказов: <b>{stats['accepted_orders']}</b>\n"
            f"💰 Общий оборот: <b>{format_currency(stats['total_revenue'])}</b>\n\n"
            f"👥 Всего клиентов в базе: <b>{stats['total_users']}</b>\n"
            f"🛢 Активных товаров: <b>{stats['total_products']}</b>"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В админ-панель", callback_data=AdminMenuCallback(menu="main").pack())]
            ]
        )
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(AdminCategoryCallback.filter())
async def admin_category_products(
    callback: CallbackQuery,
    callback_data: AdminCategoryCallback,
    session: AsyncSession,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.answer()
    product_service = ProductService(session)
    category = await product_service.get_category_by_id(callback_data.category_id)
    if not category:
        await callback.message.answer("Категория не найдена.")
        return

    # In admin mode, list all products including inactive ones
    products, total_count, total_pages = await product_service.get_products_by_category(
        category_id=category.id,
        only_active=False,
        page=callback_data.page,
        page_size=8,
    )

    action_label = "изменения цены" if callback_data.action == "edit_price_in" else "управления"
    text = (
        f"📁 <b>{category.name}</b> (Товаров: {total_count})\n\n"
        f"Выберите товар для {action_label}:\n"
        "🟢 — активен (виден клиентам)\n"
        "🔴 — отключён (скрыт из каталога)"
    )
    kb = get_admin_products_keyboard(
        products=products,
        category_id=category.id,
        action=callback_data.action,
        page=callback_data.page,
        total_pages=total_pages,
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(AdminProductCallback.filter())
async def admin_product_action(
    callback: CallbackQuery,
    callback_data: AdminProductCallback,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    product_service = ProductService(session)
    product = await product_service.get_product_by_id(callback_data.product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    if callback_data.action == "edit_price_in" or callback_data.action == "edit_price":
        await callback.answer()
        await state.set_state(EditPriceState.waiting_for_price)
        await state.update_data(
            product_id=product.id,
            category_id=callback_data.category_id,
            page=callback_data.page,
            old_price=product.price,
            product_name=product.name,
        )
        vol = f" ({product.volume})" if product.volume else ""
        text = (
            f"💰 <b>Изменение цены</b>\n\n"
            f"Товар: <b>{product.name}{vol}</b>\n"
            f"Текущая цена: <b>{format_currency(product.price)}</b>\n\n"
            "Введите новую цену (число, например <code>9000</code>):"
        )
        await callback.message.answer(text, reply_markup=get_admin_cancel_keyboard(), parse_mode="HTML")

    elif callback_data.action == "view":
        await callback.answer()
        vol = f" ({product.volume})" if product.volume else ""
        status_text = "🟢 Включён (отображается в каталоге)" if product.is_active else "🔴 Отключён (скрыт от клиентов)"
        text = (
            f"🛢 <b>{product.name}{vol}</b>\n\n"
            f"Категория: {product.category.name if product.category else '-'}\n"
            f"Вязкость: {product.viscosity or '-'}\n"
            f"Объём: {product.volume or '-'}\n"
            f"Тара: {product.package or '-'}\n"
            f"Артикул: {product.article or '-'}\n"
            f"Цена: <b>{format_currency(product.price)}</b>\n"
            f"Статус: <b>{status_text}</b>"
        )
        kb = get_admin_product_detail_keyboard(product, callback_data.category_id, callback_data.page)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    elif callback_data.action == "toggle":
        updated_prod = await product_service.toggle_active(product.id)
        st = "включён" if updated_prod.is_active else "отключён"
        await callback.answer(f"Товар {st}!")
        vol = f" ({updated_prod.volume})" if updated_prod.volume else ""
        status_text = "🟢 Включён (отображается в каталоге)" if updated_prod.is_active else "🔴 Отключён (скрыт от клиентов)"
        text = (
            f"🛢 <b>{updated_prod.name}{vol}</b>\n\n"
            f"Категория: {updated_prod.category.name if updated_prod.category else '-'}\n"
            f"Вязкость: {updated_prod.viscosity or '-'}\n"
            f"Объём: {updated_prod.volume or '-'}\n"
            f"Тара: {updated_prod.package or '-'}\n"
            f"Артикул: {updated_prod.article or '-'}\n"
            f"Цена: <b>{format_currency(updated_prod.price)}</b>\n"
            f"Статус: <b>{status_text}</b>"
        )
        kb = get_admin_product_detail_keyboard(updated_prod, callback_data.category_id, callback_data.page)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    elif callback_data.action == "delete":
        await product_service.delete_product(product.id)
        await callback.answer("Товар удален / деактивирован")
        # Return to category products list
        products, total_count, total_pages = await product_service.get_products_by_category(
            category_id=callback_data.category_id,
            only_active=False,
            page=callback_data.page,
            page_size=8,
        )
        kb = get_admin_products_keyboard(
            products=products,
            category_id=callback_data.category_id,
            action="view",
            page=callback_data.page,
            total_pages=total_pages,
        )
        await callback.message.edit_text(
            f"Товар был удален. Всего товаров: {total_count}", reply_markup=kb, parse_mode="HTML"
        )


@router.message(EditPriceState.waiting_for_price)
async def process_price_update(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if not is_admin(message.from_user.id):
        return

    text = message.text.replace(" ", "").replace(",", ".").strip()
    try:
        new_price = float(text)
        if new_price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите корректное положительное число для цены (например, <code>9500</code>):", parse_mode="HTML")
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    old_price = data.get("old_price", 0)
    product_name = data.get("product_name", "Товар")

    product_service = ProductService(session)
    await product_service.update_price(product_id, new_price)
    await state.clear()

    response_text = (
        "✅ <b>Цена успешно изменена!</b>\n\n"
        f"Товар: <b>{product_name}</b>\n"
        f"Было: <b>{format_currency(old_price)}</b>\n"
        f"Стало: <b>{format_currency(new_price)}</b>\n\n"
        "<i>Новая цена будет использоваться для всех новых заказов. История старых заказов сохранена без изменений.</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ В админ-панель", callback_data=AdminMenuCallback(menu="main").pack())],
            [InlineKeyboardButton(text="🛢 Каталог", callback_data="open_catalog")],
        ]
    )
    await message.answer(response_text, reply_markup=kb, parse_mode="HTML")


# ================= FSM Wizard: Add Product =================

@router.callback_query(F.data.startswith("adm_add_cat_"))
async def fsm_add_product_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    category_id = int(callback.data.replace("adm_add_cat_", ""))
    await state.update_data(category_id=category_id)
    await state.set_state(AddProductState.waiting_for_name)
    await callback.message.answer(
        "Шаг 2/8: Введите <b>название товара</b> (например, <code>Toyo 5W-30 API SP</code>):",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_name)
async def fsm_add_product_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Название слишком короткое. Введите название товара:")
        return
    await state.update_data(name=name)
    await state.set_state(AddProductState.waiting_for_price)
    await message.answer("Шаг 3/8: Введите <b>цену</b> в тенге (число, например <code>13500</code>):", parse_mode="HTML")


@router.message(AddProductState.waiting_for_price)
async def fsm_add_product_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace(" ", "").replace(",", ".").strip()
    try:
        price = float(text)
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Введите корректную цену (число больше 0):")
        return

    await state.update_data(price=price)
    await state.set_state(AddProductState.waiting_for_viscosity)
    await message.answer(
        "Шаг 4/8: Введите <b>вязкость</b> (например, <code>5W-30</code>) или отправьте <code>-</code> чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_viscosity)
async def fsm_add_product_viscosity(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    visc = message.text.strip()
    await state.update_data(viscosity=None if visc in ["-", "—", "нет"] else visc)
    await state.set_state(AddProductState.waiting_for_volume)
    await message.answer(
        "Шаг 5/8: Введите <b>объём</b> (например, <code>4 л</code> или <code>208 л</code>) или отправьте <code>-</code>:",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_volume)
async def fsm_add_product_volume(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    vol = message.text.strip()
    await state.update_data(volume=None if vol in ["-", "—", "нет"] else vol)
    await state.set_state(AddProductState.waiting_for_package)
    await message.answer(
        "Шаг 6/8: Введите <b>тип тары / упаковки</b> (например, <code>металл</code>, <code>пластик</code>, <code>бочка</code>) или <code>-</code>:",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_package)
async def fsm_add_product_package(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    pkg = message.text.strip()
    await state.update_data(package=None if pkg in ["-", "—", "нет"] else pkg)
    await state.set_state(AddProductState.waiting_for_article)
    await message.answer(
        "Шаг 7/8: Введите <b>артикул</b> или отправьте <code>-</code> чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_article)
async def fsm_add_product_article(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    art = message.text.strip()
    await state.update_data(article=None if art in ["-", "—", "нет"] else art)
    await state.set_state(AddProductState.waiting_for_description)
    await message.answer(
        "Шаг 8/8: Введите <b>описание / примечание</b> к товару или отправьте <code>-</code>:",
        parse_mode="HTML",
    )


@router.message(AddProductState.waiting_for_description)
async def fsm_add_product_desc(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if not is_admin(message.from_user.id):
        return
    desc = message.text.strip()
    desc_val = None if desc in ["-", "—", "нет"] else desc

    data = await state.get_data()
    product_service = ProductService(session)

    new_prod = await product_service.create_product(
        category_id=data["category_id"],
        name=data["name"],
        price=data["price"],
        viscosity=data.get("viscosity"),
        volume=data.get("volume"),
        package=data.get("package"),
        article=data.get("article"),
        description=desc_val,
    )
    await state.clear()

    text = (
        "🎉 <b>Товар успешно добавлен в базу данных!</b>\n\n"
        f"🛢 <b>{new_prod.name}</b>\n"
        f"Цена: <b>{format_currency(new_prod.price)}</b>\n"
        f"Вязкость: {new_prod.viscosity or '-'}\n"
        f"Объём: {new_prod.volume or '-'}\n"
        f"Фасовка: {new_prod.package or '-'}\n"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё", callback_data=AdminMenuCallback(menu="add_product").pack())],
            [InlineKeyboardButton(text="⚙️ В админ-панель", callback_data=AdminMenuCallback(menu="main").pack())],
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
