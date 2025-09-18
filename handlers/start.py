import os

from aiogram import Router, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from database.db import async_session
from database.models import User
from logger import app_logger
from utils.keyboards import back_menu_button, main_menu_kb

router = Router()

@router.message(Command('start'))
async def start_cmd(message: types.Message):
    user = message.from_user

    if user is None:
        await message.answer("Ошибка: не удалось определить пользователя.")
        return

    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == user.id)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
        is_admin = user.id in admin_ids

        if db_user is None:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                is_admin=is_admin
            )
            session.add(db_user)
            await session.commit()
            app_logger.info(f"🆕 Новый пользователь: {user.id} | @{user.username or '-'} | is_admin=False")
        else:
            is_admin = bool(db_user.is_admin)

        # Ещё раз: db_user уже точно не None, проверяем is_admin
        if db_user.is_admin is not True:
            await message.answer("⛔ У тебя нет прав для использования бота.")
            app_logger.info(f"⛔ Доступ запрещён обычному пользователю: {user.id} | @{user.username or '-'}")
            return


        # Только для админа — показываем кнопку
        kb = main_menu_kb()

    try:
        await message.answer(
            "Привет, админ! 👋\nТы можешь использовать команды для работы с ботом.",
            reply_markup=kb
        )
        app_logger.info(f"✅ Админ зашёл в бота: {user.id} | @{user.username or '-'}")
    except TelegramForbiddenError:
        app_logger.warning(f"❌ Пользователь {user.id} заблокировал бота.")


@router.callback_query(lambda c: c.data == "view_database")
async def handle_view_database(callback: CallbackQuery):
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Посмотреть отчёт", callback_data="view_report")],
        [InlineKeyboardButton(text="📊 Экспорт в Excel", callback_data="export_excel")],
        [InlineKeyboardButton(text="📋 Все субботники", callback_data="view_events")],
        [InlineKeyboardButton(text="👥 Все команды", callback_data="view_teams")],
        *back_menu_button()
    ])

    try:
        await callback.message.edit_text("Что ты хочешь посмотреть?", reply_markup=kb) # type: ignore
    except Exception:
        await callback.message.delete() # type: ignore
        await callback.message.answer("Что ты хочешь посмотреть?", reply_markup=kb) # type: ignore
