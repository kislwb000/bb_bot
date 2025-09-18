from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Event, Team
from utils.constants import CATEGORIES
from utils.keyboards import back_button

router = Router()

@router.callback_query(lambda c: c.data == "view_report")
async def handle_report_start(callback: CallbackQuery):
    await callback.answer()

    async with async_session() as session:
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await session.execute(stmt)
        events = result.scalars().all()

    if not events:
        await callback.message.answer("❗ Нет доступных субботников.") # type: ignore
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        *[
            [InlineKeyboardButton(text=event.title, callback_data=f"report_event:{event.id}")]
            for event in events
        ],
        *back_button('back_to_main')

    ])
    await callback.message.answer("Выберите субботник для отчёта:", reply_markup=kb) # type: ignore

@router.callback_query(lambda c: c.data.startswith("report_event:"))
async def handle_report_data(callback: CallbackQuery):
    await callback.answer()
    event_id = int(callback.data.split(":")[1]) # type: ignore

    async with async_session() as session:
        stmt = (
            select(Team)
            .where(Team.event_id == event_id)
            .options(selectinload(Team.scores))
            .order_by(Team.name)
        )
        result = await session.execute(stmt)
        teams = result.scalars().all()

    if not teams:
        await callback.message.answer("❗ В этом субботнике пока нет команд.") # type: ignore
        return

    text = "<b>📊 Итоги субботника:</b>\n\n"

    # Считаем и сортируем команды по сумме баллов
    teams_with_totals = []
    for team in teams:
        total = sum(score.points for score in team.scores)
        teams_with_totals.append((team, total))

    # Сортировка по убыванию баллов
    teams_with_totals.sort(key=lambda x: x[1], reverse=True)

    # Формируем текст
    for idx, (team, total) in enumerate(teams_with_totals, start=1):
        text += f"<b>{idx}. {team.name}</b>\n"

        if not team.scores:
            text += "— Нет начисленных баллов\n\n"
            continue

        for score in team.scores:
            cat_title = CATEGORIES.get(score.category, (score.category, ""))[0]
            text += f"{cat_title}: {score.points} баллов\n"

        text += f"<b>Итого: {total} баллов</b>\n\n"


    kb2 = InlineKeyboardMarkup(inline_keyboard=[
        *back_button('view_database')
    ])

    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb2) # type: ignore
