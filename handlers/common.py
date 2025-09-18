from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from utils.keyboards import main_menu_kb

router = Router()

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()

    try:
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_kb()) # type: ignore
    except Exception:
        await callback.message.delete() # type: ignore
        await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_kb()) # type: ignore
