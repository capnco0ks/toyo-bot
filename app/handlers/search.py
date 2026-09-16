from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import ProductService
from app.states.search_states import SearchState
from app.utils.callback_factories import ProductCallback

router = Router(name="search")


@router.message(F.text == "🔎 Поиск")
@router.callback_query(F.data == "start_search")
async def start_search_handler(
    event: Message | CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(SearchState.waiting_for_query)
    text = (
        "🔎 <b>Поиск по каталогу</b>\n\n"
        "Введите наименование, вязкость (например, <code>5W-30</code>, <code>10W-40</code>, <code>ATF</code>), "
        "артикул или тип фасовки:"
    )
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="open_catalog")]
        ]
    )

    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message.photo:
            await event.message.delete()
            await event.message.answer(text, reply_markup=cancel_kb, parse_mode="HTML")
        else:
            await event.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=cancel_kb, parse_mode="HTML")


@router.message(SearchState.waiting_for_query)
async def process_search_query(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("⚠️ Поисковый запрос должен содержать минимум 2 символа. Попробуйте еще раз:")
        return

    await state.clear()
    product_service = ProductService(session)
    products, total_count, _ = await product_service.search_products(
        query=query, only_active=True, page=1, page_size=15
    )

    if not products:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔎 Искать снова", callback_data="start_search")],
                [InlineKeyboardButton(text="🛢 Каталог", callback_data="open_catalog")],
            ]
        )
        await message.answer(
            f"По запросу «<b>{query}</b>» ничего не найдено.\n"
            "Попробуйте изменить запрос (например, ввести только вязкость <code>5w30</code> или <code>CVT</code>).",
            reply_markup=kb,
            parse_mode="HTML",
        )
        return

    buttons = []
    for prod in products:
        vol = f" ({prod.volume})" if prod.volume else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"🛢 {prod.name}{vol}",
                callback_data=ProductCallback(product_id=prod.id, category_id=prod.category_id, page=1).pack(),
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔎 Новый поиск", callback_data="start_search"),
        InlineKeyboardButton(text="🛢 Каталог", callback_data="open_catalog"),
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🔎 Результаты поиска по запросу «<b>{query}</b>» (найдено: {total_count}):\n\n"
        "Выберите товар для добавления в заказ:",
        reply_markup=kb,
        parse_mode="HTML",
    )
