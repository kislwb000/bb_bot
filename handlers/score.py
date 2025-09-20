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
from database.models import Event, Score, Team
from logger import app_logger
from states.score import ScoreStates
from utils.constants import CATEGORIES
from utils.keyboards import back_button, back_menu_button

router = Router()

ITEMS_PER_PAGE = 10  # Кол-во команд на одной странице


def get_score_teams_kb(
    teams, page: int, total_pages: int, callback_base: str = "score_team"
) -> InlineKeyboardMarkup:
    """
    Формируем InlineKeyboard с командами текущей страницы
    и навигационными кнопками.
    """
    buttons = []

    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    teams_page = teams[start:end]

    # Кнопки с командами
    for team in teams_page:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=team.name, callback_data=f"{callback_base}:{team.id}"
                )
            ]
        )

    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"score_team_page:{page - 1}"
            )
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Далее", callback_data=f"score_team_page:{page + 1}"
            )
        )
    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка "назад"
    buttons.extend(back_button("score_start"))

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(lambda c: c.data == "score_start")
async def handle_score_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await score_start(
        callback.message, state
    )  # 👈 вызываем существующий хендлер команд


@router.message(Command("score"))
async def score_start(message: Message, state: FSMContext):
    async with async_session() as session:
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await session.execute(stmt)
        events = result.scalars().all()

    if not events:
        await message.answer("❗ Пока нет ни одного субботника.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=event.title, callback_data=f"score_event:{event.id}"
                )
            ]
            for event in events
        ]
    )
    await message.answer("Выберите субботник для начисления баллов:", reply_markup=kb)
    await state.set_state(ScoreStates.waiting_for_event)


@router.callback_query(
    StateFilter(ScoreStates.waiting_for_event),
    lambda c: c.data.startswith("score_event:"),
)
async def select_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    event_id = int(callback.data.split(":")[1])
    await state.update_data(event_id=event_id, page=1)  # сохраняем текущую страницу

    async with async_session() as session:
        stmt = select(Team).where(Team.event_id == event_id).order_by(Team.id)
        result = await session.execute(stmt)
        teams = result.scalars().all()

    if not teams:
        await callback.message.answer("❗ В этом субботнике пока нет команд.")
        await state.clear()
        return

    total_pages = (len(teams) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    kb = get_score_teams_kb(teams, page=1, total_pages=total_pages)

    await callback.message.answer(
        "Выберите команду для начисления баллов:", reply_markup=kb
    )
    await state.set_state(ScoreStates.waiting_for_team)
    await state.update_data(
        teams_list=[team.id for team in teams], total_pages=total_pages
    )


@router.callback_query(
    StateFilter(ScoreStates.waiting_for_team),
    lambda c: c.data.startswith("score_team_page:"),
)
async def change_team_page(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    teams_ids = data.get("teams_list", [])
    total_pages = data.get("total_pages", 1)

    async with async_session() as session:
        stmt = select(Team).where(Team.id.in_(teams_ids)).order_by(Team.id)
        result = await session.execute(stmt)
        teams = result.scalars().all()

    kb = get_score_teams_kb(teams, page=page, total_pages=total_pages)
    await state.update_data(page=page)

    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except:
        await callback.message.answer("Выберите команду:", reply_markup=kb)


@router.callback_query(
    StateFilter(ScoreStates.waiting_for_team),
    lambda c: c.data.startswith("score_team:"),
)
async def select_team(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    team_id = int(callback.data.split(":")[1])  # type: ignore
    await state.update_data(team_id=team_id)

    # Получаем название команды
    async with async_session() as session:
        stmt = select(Team).where(Team.id == team_id)
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=title, callback_data=f"score_cat:{key}")]
            for key, (title, points, count_type) in CATEGORIES.items()
        ]
        + [[InlineKeyboardButton(text="🚫 Завершить", callback_data="score_stop")]]
    )

    await callback.message.answer(  # type: ignore
        f"Выберите категорию для начисления баллов команде <b>{team.name}</b>:",  # type: ignore
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data.startswith("score_cat:"))
async def apply_score(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    cat_key = callback.data.split(":")[1]  # type: ignore

    if cat_key not in CATEGORIES:
        await callback.message.answer("❌ Неизвестная категория.")  # type: ignore
        return

    cat_title, points, count_type = CATEGORIES[cat_key]
    await state.update_data(category=cat_key)

    if isinstance(points, list):
        # Категория с ручным выбором баллов
        # Показываем кнопки с вариантами
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=str(p), callback_data=f"score_points:{p}")
                    for p in points[i : i + 3]
                ]
                for i in range(0, len(points), 3)
            ]
            + [[InlineKeyboardButton(text="↩️ Назад", callback_data="score_cancel")]]
        )

        await callback.message.answer(  # type: ignore
            f"Выберите, сколько баллов начислить за <b>{cat_title}</b>:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        await state.set_state(ScoreStates.waiting_for_custom_points)
        return

    # Фиксированная категория (int)
    await state.update_data(points=points)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="score_confirm"
                ),
                InlineKeyboardButton(text="🚫 Отклонить", callback_data="score_reject"),
            ]
        ]
    )
    await callback.message.answer(  # type: ignore
        f"Начислить <b>{points}</b> баллов по категории <b>{cat_title}</b>?",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await state.set_state(ScoreStates.confirming_score)


@router.callback_query(
    StateFilter(ScoreStates.waiting_for_custom_points),
    lambda c: c.data.startswith("score_points:"),
)
async def handle_custom_points(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    points = int(callback.data.split(":")[1])  # type: ignore
    data = await state.get_data()
    cat_key = data.get("category")
    cat_title = CATEGORIES[cat_key][0]  # type: ignore

    await state.update_data(points=points)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="score_confirm"
                ),
                InlineKeyboardButton(text="🚫 Отклонить", callback_data="score_reject"),
            ]
        ]
    )
    await callback.message.answer(  # type: ignore
        f"Начислить <b>{points}</b> баллов по категории <b>{cat_title}</b>?",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await state.set_state(ScoreStates.confirming_score)


@router.callback_query(lambda c: c.data == "score_cancel")
async def handle_score_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    team_id = data.get("team_id")

    async with async_session() as session:
        stmt = select(Team).where(Team.id == team_id)
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=title, callback_data=f"score_cat:{key}")]
            for key, (title, points, count_type) in CATEGORIES.items()
        ]
        + [[InlineKeyboardButton(text="🛑 Завершить", callback_data="score_stop")]]
    )

    await callback.message.answer(  # type: ignore
        f"Выберите категорию для начисления баллов команде <b>{team.name}</b>:",  # type: ignore
        parse_mode="HTML",
        reply_markup=kb,
    )
    await state.set_state(ScoreStates.waiting_for_team)


@router.callback_query(lambda c: c.data == "score_stop")
async def handle_score_stop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[*back_button("score_start"), *back_menu_button()]
    )

    await callback.message.answer(  # type: ignore
        "✅ Проставление баллов завершено.\nМожешь вернуться в меню или продолжить работу.",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(
    StateFilter(ScoreStates.confirming_score), lambda c: c.data == "score_confirm"
)
async def confirm_score(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    team_id = data.get("team_id")
    category = data.get("category")
    points = data.get("points")

    if not team_id or not category:
        await callback.message.answer("⚠️ Ошибка: не хватает данных.")  # type: ignore
        await state.clear()
        return

    async with async_session() as session:
        stmt = select(Score).where(Score.team_id == team_id, Score.category == category)
        result = await session.execute(stmt)
        score = result.scalar_one_or_none()

        score = Score(team_id=team_id, category=category, points=points)
        session.add(score)

        stmt_team = select(Team).where(Team.id == team_id)
        result_team = await session.execute(stmt_team)
        team = result_team.scalar_one_or_none()

        await session.commit()

        app_logger.info(
            f"🎯 Начислены баллы: {points} | Категория: '{category}' → Команда: '{team.name}' | Субботник ID: {team.event_id}"
        )  # type: ignore

        await callback.message.answer(  # type: ignore
            f"✅ Баллы начислены: <b>{points}</b> по категории <b>{CATEGORIES[category][0]}</b>.",
            parse_mode="HTML",
        )

        # Показываем меню категорий снова
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=title, callback_data=f"score_cat:{key}")]
                for key, (title, points, count_type) in CATEGORIES.items()
            ]
            + [[InlineKeyboardButton(text="🚫 Завершить", callback_data="score_stop")]]
        )

        await callback.message.answer(
            "Выберите следующую категорию для начисления баллов:", reply_markup=kb
        )  # type: ignore
        await state.set_state(ScoreStates.waiting_for_team)


@router.callback_query(
    StateFilter(ScoreStates.confirming_score), lambda c: c.data == "score_reject"
)
async def reject_score(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    team_id = data.get("team_id")

    async with async_session() as session:
        stmt = select(Team).where(Team.id == team_id)
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=title, callback_data=f"score_cat:{key}")]
            for key, (title, points, count_type) in CATEGORIES.items()
        ]
        + [[InlineKeyboardButton(text="🚫 Завершить", callback_data="score_stop")]]
    )

    await callback.message.answer(  # type: ignore
        f"Выберите категорию для начисления баллов команде <b>{team.name}</b>:",  # type: ignore
        parse_mode="HTML",
        reply_markup=kb,
    )

    await state.set_state(ScoreStates.waiting_for_team)
