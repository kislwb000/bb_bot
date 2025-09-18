from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin_instruction")],
            [InlineKeyboardButton(text="🗓️ Создать субботник", callback_data="create_event")],
            [InlineKeyboardButton(text="👥 Добавить команду", callback_data="add_team")],
            [InlineKeyboardButton(text="📂 Просмотреть базу данных", callback_data="view_database")],
            [InlineKeyboardButton(text="📊 Проставить баллы", callback_data="score_start")],
            [InlineKeyboardButton(text="⚙️ Управление баллами", callback_data="adjust_score_start")]
        ])

def back_menu_button() -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]]

def back_button(callback_to_return: str = "back_to_main") -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="🔙 Назад", callback_data=callback_to_return)]]

def add_more(callback_to_return: str = "back_to_main") -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="Добавить еще команду", callback_data=callback_to_return)]]
