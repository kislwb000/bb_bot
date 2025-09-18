
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select

from database.db import async_session
from database.models import User
from logger import app_logger
from states.add_admin import AddAdmin
from utils.keyboards import back_button

router = Router()

kb = InlineKeyboardMarkup(inline_keyboard=[*back_button('back_to_main')])

# Обработка нажатия кнопки "Добавить админа"
@router.callback_query(lambda c: c.data == "add_admin_instruction")
async def ask_for_username(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddAdmin.waiting_for_username)
    if callback.message:
        await callback.message.answer("Введите username пользователя, которого хотите назначить админом (например: @ivanov)", reply_markup=kb)

# Обработка ввода username
@router.message(StateFilter(AddAdmin.waiting_for_username))
async def process_username(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ Введите текст — username пользователя.", reply_markup=kb)
        return

    raw_username = message.text.strip()

    if raw_username.startswith("@"):
        raw_username = raw_username[1:]

    if not raw_username:
        await message.answer("⚠️ Username не может быть пустым.", reply_markup=kb)
        return

    async with async_session() as session:
        stmt = select(User).where(User.username.ilike(raw_username))
        result = await session.execute(stmt)
        user: User | None = result.scalar_one_or_none()

        if user is None:
            await message.answer(
                f"❌ Пользователь с username `{raw_username}` не найден в базе.",
                parse_mode="HTML", reply_markup=kb
            )
        elif bool(user.is_admin):
            await message.answer("⚠️ Этот пользователь уже является админом.", reply_markup=kb)
        else:
            user.is_admin = True
            await session.commit()
            app_logger.info(f"🔐 Добавлен админ: {user.telegram_id} | @{user.username or '-'} — добавил: {message.from_user.id} | @{message.from_user.username or '-'}") # type:ignore
            await message.answer(
                f"✅ Пользователь @{user.username} теперь админ!",
                parse_mode="HTML", reply_markup=kb
            )

    await state.clear()
