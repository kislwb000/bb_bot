import os

from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import Event, Team
from logger import app_logger
from utils.constants import CATEGORIES  # 📦 наш словарь с категориями
from utils.keyboards import back_button, back_menu_button

router = Router()


# 📦 Кнопка "Экспорт в Excel"
@router.callback_query(lambda c: c.data == "export_excel")
async def handle_export_excel_start(callback: CallbackQuery):
    await callback.answer()

    async with async_session() as session:
        stmt = select(Event).order_by(Event.created_at.desc())
        result = await session.execute(stmt)
        events = result.scalars().all()

    if not events:
        await callback.message.edit_text("❗ Субботники не найдены.")  # type: ignore
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=event.title, callback_data=f"export_event:{event.id}"
                )
            ]
            for event in events
        ]
        + back_button("view_database")
    )

    await callback.message.edit_text(
        "📁 Выбери субботник для экспорта:", reply_markup=kb
    )  # type: ignore


# 📄 Обработка выбора субботника
@router.callback_query(lambda c: c.data and c.data.startswith("export_event:"))
async def handle_export_event(callback: CallbackQuery):
    await callback.answer()
    event_id = int(callback.data.split(":")[1])  # type: ignore

    async with async_session() as session:
        stmt = (
            select(Team)
            .where(Team.event_id == event_id)
            .options(selectinload(Team.scores))
        )
        teams_result = await session.execute(stmt)
        teams = teams_result.scalars().all()

    if not teams:
        await callback.message.edit_text("❗ У этого субботника пока нет команд.")  # type: ignore
        return

    # 📊 Загружаем категории
    category_keys = list(CATEGORIES.keys())
    category_titles = {
        key: title for key, (title, points, count_type) in CATEGORIES.items()
    }

    # 🧾 Создание Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчёт"  # type: ignore

    # 🔠 Заголовки
    headers = (
        ["Команда"] + [category_titles[key] for key in category_keys] + ["Всего баллов"]
    )
    ws.append(headers)  # type: ignore

    # Устанавливаем ширину столбцов
    ws.column_dimensions["A"].width = 80  # type: ignore
    col_letters = "BCDEFGHIJKLMNOPQRSTUVWXYZ"  # на случай большого количества категорий
    for idx, key in enumerate(category_keys):
        ws.column_dimensions[col_letters[idx]].width = 30  # type: ignore
    ws.column_dimensions[col_letters[len(category_keys)]].width = 18  # type: ignore

    rows = []

    for team in teams:
        row = [team.name]
        total = 0

        for key in category_keys:
            score = next((s.points for s in team.scores if s.category == key), 0)
            row.append(score)  # type: ignore
            total += score

        row.append(total)  # type: ignore
        rows.append(row)

    # 🔽 Сортировка по общему баллу (последняя колонка)
    rows.sort(key=lambda x: x[-1], reverse=True)

    # 📥 Запись в Excel
    for row in rows:
        ws.append(row)  # type: ignore

    ws.append([])  # type: ignore

    # 🧮 Подсчёт мешков по категориям (для всего субботника)
    category_totals = {key: 0 for key in category_keys}

    for team in teams:
        for score in team.scores:
            if score.category in category_totals:
                category_totals[score.category] += 1

    # 📦 Добавим итоги по категориям только один раз
    ws.append([])  # пустая строка перед итогами # type: ignore
    ws.append(["ИТОГО по категориям (мешки):"])  # type: ignore
    for key in category_keys:
        cat_title = category_titles[key]
        total_bags = category_totals[key]
        ws.append([f"{cat_title}", total_bags])  # type: ignore

    filename = f"event_{event_id}_report.xlsx"
    wb.save(filename)

    event_id = int(callback.data.split(":")[1])  # type: ignore
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[*back_button("view_database"), *back_menu_button()]
    )

    # 📤 Отправка
    await callback.message.answer_document(
        FSInputFile(path=filename, filename=filename), reply_markup=kb
    )  # type: ignore
    app_logger.info(
        f"📤 Экспорт Excel: Субботник '{event.title}' (ID {event.id}) — админ {callback.from_user.id} | @{callback.from_user.username or '-'}"
    )  # type: ignore
    os.remove(filename)
