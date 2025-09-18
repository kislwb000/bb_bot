from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from database.db import async_session
from database.models import Event, Team
from logger import app_logger
from states.team import TeamStates
from utils.keyboards import add_more, back_button, back_menu_button

router = Router()

# 🔘 Команда: /add_team
@router.message(Command("add_team"))
async def add_team_command(message: Message, state: FSMContext):
    async with async_session() as session:
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await session.execute(stmt)
        events = result.scalars().all()

    kb2 = InlineKeyboardMarkup(inline_keyboard=[*back_button('back_to_main')])

    if not events:
        await message.answer("⚠️ Пока нет ни одного субботника.", reply_markup=kb2)
        return

    # 👇 Формируем кнопки с data=event:<id>
    buttons = [
        *[[InlineKeyboardButton(text=event.title, callback_data=f"event:{event.id}")]
        for event in events],
        *back_button('back_to_main')
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "Выберите субботник, к которому хотите добавить команду:",
        reply_markup=kb
    )
    await state.set_state(TeamStates.waiting_for_event_title)


# 🔁 Callback из кнопки "Добавить команду" в start.py
@router.callback_query(lambda c: c.data == "add_team")
async def handle_add_team_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await add_team_command(callback.message, state)  # type: ignore


# ✅ Обработка выбора субботника (event:<id>)
@router.callback_query(StateFilter(TeamStates.waiting_for_event_title), lambda c: c.data and c.data.startswith("event:"))
async def process_event_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        event_id = int(callback.data.split(":")[1])  # type: ignore
    except (IndexError, ValueError):
        await callback.message.answer("❌ Ошибка: не удалось определить субботник.") # type: ignore
        return

    await state.update_data(event_id=event_id)
    await callback.message.answer("Введите название команды:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[*back_button('add_team')])) # type: ignore
    await state.set_state(TeamStates.waiting_for_team_name)


# 📝 Обработка названия команды
@router.message(StateFilter(TeamStates.waiting_for_team_name))
async def process_team_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❗ Название команды не может быть пустым.")
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    team_name = message.text.strip()

    async with async_session() as session:
        # Получаем название субботника
        stmt = select(Event).where(Event.id == event_id)
        result = await session.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            await message.answer("⚠️ Ошибка: не удалось найти субботник.")
            await state.clear()
            return

        # Добавляем команду
        new_team = Team(name=team_name, event_id=event_id)
        session.add(new_team)
        await session.commit()
        app_logger.info(f"👥 Команда добавлена: '{team_name}' → Субботник: '{event.title}' (ID {event.id})")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        *add_more('add_team'),
        *back_menu_button()
    ])

    await message.answer(
        f"✅ Команда <b>{team_name}</b> добавлена к субботнику <b>{event.title}</b>.",
        parse_mode="HTML", reply_markup=kb
    )
    await state.clear()

