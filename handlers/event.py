from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from database.db import async_session
from database.models import Event
from logger import app_logger
from states.event import EventStates
from utils.keyboards import back_button

router = Router()

kb = InlineKeyboardMarkup(inline_keyboard=[*back_button('back_to_main')])

@router.callback_query(lambda c: c.data == "create_event")
async def handle_create_event_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    try:
        await callback.message.answer("Введите название субботника:") # type: ignore
    except AttributeError:
        await callback.bot.send_message(callback.from_user.id, "Введите название субботника:") # type: ignore

    await state.set_state(EventStates.waiting_for_title)


# 🔘 Кнопка "Создать субботник"
@router.message(Command("create_event"))
async def create_event(message: Message, state: FSMContext):
    await message.answer("Введите название субботника:", reply_markup=kb)
    await state.set_state(EventStates.waiting_for_title)

# 📝 Обработка названия субботника
@router.message(StateFilter(EventStates.waiting_for_title))
async def process_event_title(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Название субботника не может быть пустым.", reply_markup=kb)
        return

    title = message.text.strip()

    telegram_id = message.from_user.id #type: ignore

    async with async_session() as session:
        new_event = Event(
            title=title,
            created_by=telegram_id,
            created_at=datetime.utcnow()
        )
        session.add(new_event)
        await session.commit()
        app_logger.info(f"📅 Субботник создан: '{title}' | админ {telegram_id} | @{message.from_user.username or '-'}") # type: ignore


    await message.answer(
    f"✅ Субботник <b>{title}</b> успешно создан!\nID: <code>{new_event.id}</code>",
    parse_mode="HTML", reply_markup=kb)
    await state.clear()
