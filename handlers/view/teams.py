from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Team
from utils.keyboards import back_button

router = Router()
ITEMS_PER_PAGE = 20  # Количество команд на одной странице


def get_teams_kb(
    page: int, total_pages: int, callback_base: str = "view_teams"
) -> InlineKeyboardMarkup:
    buttons = []

    # Навигационные кнопки
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"{callback_base}:{page - 1}"
            )
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Далее", callback_data=f"{callback_base}:{page + 1}"
            )
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка "назад"
    buttons.extend(back_button("view_database"))

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(lambda c: c.data.startswith("view_teams"))
async def handle_view_teams(callback: types.CallbackQuery):
    await callback.answer()

    # Получаем номер страницы из callback_data
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 1

    async with async_session() as session:
        stmt = select(Team).options(selectinload(Team.event)).order_by(Team.event_id)
        result = await session.execute(stmt)
        teams = result.scalars().all()

    if not teams:
        await callback.message.answer(
            "📭 Список команд пуст.", reply_markup=back_button("view_database")[0]
        )  # type: ignore
        return

    total_pages = (len(teams) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    teams_page = teams[start:end]

    text = f"<b>👥 Список команд (страница {page}/{total_pages}):</b>\n\n"
    for team in teams_page:
        event_title = team.event.title if team.event else "❓ Неизвестный субботник"
        text += f"• <b>{team.name}</b> — <i>{event_title}</i>\n"

    kb = get_teams_kb(page, total_pages)
    # Если сообщение уже есть, редактируем, иначе отправляем новое
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
