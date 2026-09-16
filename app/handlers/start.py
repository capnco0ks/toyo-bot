from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.keyboards.main_kb import (
    get_main_reply_keyboard,
    get_contact_manager_keyboard,
)
from app.config import settings

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    welcome_text = (
        f"👋 Здравствуйте, <b>{user.full_name}</b>!\n\n"
        "Добро пожаловать в оптовый каталог моторных и трансмиссионных масел <b>TOYO</b>.\n\n"
        "Здесь вы можете:\n"
        "• Просмотреть актуальный оптовый прайс и наличие\n"
        "• Добавить нужные позиции и бочки в корзину\n"
        "• Быстро сформировать и отправить заказ менеджеру\n"
        "• Отслеживать историю и статусы своих заказов\n\n"
        "Выберите интересующий раздел в меню ниже 👇"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_keyboard(message.from_user.id),
        parse_mode="HTML",
    )


@router.message(F.text == "❌ Отмена")
@router.message(F.text == "🏠 Главное меню")
async def cmd_cancel_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_reply_keyboard(message.from_user.id),
    )


@router.callback_query(F.data == "open_main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_reply_keyboard(callback.from_user.id),
    )


@router.message(F.text == "📞 Связаться с менеджером")
async def cmd_contact_manager(message: Message) -> None:
    manager_user = settings.MANAGER_USERNAME.lstrip("@")
    text = (
        "📞 <b>Контакты оптового отдела:</b>\n\n"
        f"👤 Менеджер по оптовым продажам: <b>@{manager_user}</b>\n"
        "⏰ График работы: Пн–Сб с 09:00 до 18:00\n\n"
        "Вы можете написать менеджеру напрямую для консультации по подбору, "
        "условиям доставки и специальным оптовым скидкам."
    )
    await message.answer(
        text,
        reply_markup=get_contact_manager_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
