from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select

from database.db import async_session
from database.models import Event
from utils.keyboards import back_button

kb = InlineKeyboardMarkup(inline_keyboard=[*back_button('view_database')])

router = Router()

@router.callback_query(lambda c: c.data == "view_events")
async def handle_view_events(callback: types.CallbackQuery):
    await callback.answer()

    async with async_session() as session:
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await session.execute(stmt)
        events = result.scalars().all()

    if not events:
        await callback.message.answer("📭 Список субботников пуст.", reply_markup=kb) # type: ignore
        return

    text = "<b>📅 Список субботников:</b>\n\n"
    for event in events:
        text += f"• <b>{event.title}</b> (ID: <code>{event.id}</code>)\n"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb) # type: ignore
