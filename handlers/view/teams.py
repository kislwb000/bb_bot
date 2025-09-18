from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Team
from utils.keyboards import back_button

kb = InlineKeyboardMarkup(inline_keyboard=[*back_button('view_database')])

router = Router()

@router.callback_query(lambda c: c.data == "view_teams")
async def handle_view_teams(callback: types.CallbackQuery):
    await callback.answer()

    async with async_session() as session:
        stmt = select(Team).options(selectinload(Team.event)).order_by(Team.event_id)
        result = await session.execute(stmt)
        teams = result.scalars().all()

    if not teams:
        await callback.message.answer("📭 Список команд пуст.", reply_markup=kb) # type: ignore
        return

    text = "<b>👥 Список всех команд:</b>\n\n"
    for team in teams:
        event_title = team.event.title if team.event else "❓ Неизвестный субботник"
        text += f"• <b>{team.name}</b> — <i>{event_title}</i>\n"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb) # type: ignore
