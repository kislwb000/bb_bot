from aiogram.fsm.state import State, StatesGroup


class ScoreManageStates(StatesGroup):
    waiting_for_event = State()
    waiting_for_team = State()
    confirming_delete = State()
    waiting_for_amount_to_subtract = State()
