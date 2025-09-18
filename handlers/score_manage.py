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
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Event, Score, Team
from logger import app_logger
from states.score_manage import ScoreManageStates
from utils.constants import CATEGORIES
from utils.keyboards import back_button, back_menu_button

router = Router()


@router.message(Command("adjust_score"))
async def adjust_score_start(message: Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(Event).order_by(Event.created_at.desc()))
        events = result.scalars().all()

    if not events:
        await message.answer("❗ Субботники пока не созданы.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=event.title, callback_data=f"adjust_event:{event.id}"
                )
            ]
            for event in events
        ]
    )
    await message.answer("Выберите субботник:", reply_markup=kb)
    await state.set_state(ScoreManageStates.waiting_for_event)


@router.callback_query(lambda c: c.data == "adjust_score_start")
async def handle_adjust_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await adjust_score_start(callback.message, state)


@router.callback_query(
    StateFilter(ScoreManageStates.waiting_for_event),
    lambda c: c.data.startswith("adjust_event:"),
)
async def adjust_select_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    event_id = int(callback.data.split(":")[1])  # type: ignore
    await state.update_data(event_id=event_id)

    async with async_session() as session:
        stmt = select(Team).where(Team.event_id == event_id).order_by(Team.name)
        result = await session.execute(stmt)

        teams = result.scalars().all()

    if not teams:
        await callback.message.answer("❗ В этом субботнике нет команд.")  # type: ignore
        await state.clear()
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=team.name, callback_data=f"adjust_team:{team.id}"
                )
            ]
            for team in teams
        ]
    )
    await callback.message.answer("Выберите команду:", reply_markup=kb)  # type: ignore
    await state.set_state(ScoreManageStates.waiting_for_team)


@router.callback_query(
    StateFilter(ScoreManageStates.waiting_for_team),
    lambda c: c.data.startswith("adjust_team:"),
)
async def adjust_select_team(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    team_id = int(callback.data.split(":")[1])  # type: ignore
    await state.update_data(team_id=team_id)
    await render_team_scores(callback.message, state)  # type: ignore


@router.callback_query(
    StateFilter(ScoreManageStates.confirming_delete),
    lambda c: c.data.startswith("adjust_delete:"),
)
async def delete_category_score(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    team_id = data.get("team_id")
    cat_key = callback.data.split(":")[1]  # type: ignore

    await state.update_data(category_to_adjust=cat_key)
    await callback.message.answer(  # type: ignore
        f"Введите, сколько баллов вычесть из категории <b>{CATEGORIES[cat_key][0]}</b>:",
        parse_mode="HTML",
    )
    await state.set_state(ScoreManageStates.waiting_for_amount_to_subtract)


@router.message(StateFilter(ScoreManageStates.waiting_for_amount_to_subtract))
async def subtract_points(message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = data.get("team_id")
    category = data.get("category_to_adjust")

    try:
        amount = int(message.text)  # type: ignore
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите положительное число.")
        return

    async with async_session() as session:
        stmt = select(Score).where(Score.team_id == team_id, Score.category == category)
        result = await session.execute(stmt)
        score = result.scalar_one_or_none()

        if not score:
            await message.answer("⚠️ Баллы по этой категории не найдены.")
            await state.clear()
            return

        score.points -= amount
        if score.points <= 0:
            session.delete(score)  # type: ignore
        await session.commit()

        app_logger.info(
            f"🔻 Вычтено {amount} баллов из '{category}' команды ID {team_id}"
        )

    await message.answer(
        f"✅ Вычтено <b>{amount}</b> баллов из категории <b>{CATEGORIES[category][0]}</b>.",
        parse_mode="HTML",
    )  # type: ignore
    await render_team_scores(message, state)


@router.callback_query(
    StateFilter(ScoreManageStates.confirming_delete),
    lambda c: c.data == "adjust_cancel",
)
async def adjust_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[*back_button("score_start"), *back_menu_button()]
    )
    await callback.message.answer("Возврат в меню управления.", reply_markup=kb)  # type: ignore


# 🔁 Общая функция отрисовки текущих баллов команды
async def render_team_scores(target_message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = data.get("team_id")

    async with async_session() as session:
        stmt = select(Team).where(Team.id == team_id).options(selectinload(Team.scores))
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()

    if not team or not team.scores:
        await target_message.answer("У этой команды пока нет баллов.")
        await state.clear()
        return

    text = f"🔧 Управление баллами — команда <b>{team.name}</b>\n\n"

    kb = []
    for score in team.scores:
        cat_title = CATEGORIES.get(score.category, (score.category, ""))[0]
        text += f"{cat_title}: <b>{score.points}</b> баллов\n"
        kb.append(
            [
                InlineKeyboardButton(
                    text=f"❌ Удалить: {cat_title}",
                    callback_data=f"adjust_delete:{score.category}",
                )
            ]
        )

    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adjust_cancel")])
    markup = InlineKeyboardMarkup(inline_keyboard=kb)

    await target_message.answer(text, parse_mode="HTML", reply_markup=markup)
    await state.set_state(ScoreManageStates.confirming_delete)
