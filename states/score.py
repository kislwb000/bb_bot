from aiogram.fsm.state import State, StatesGroup


class ScoreStates(StatesGroup):
    waiting_for_event = State()
    waiting_for_team = State()
    confirming_score = State()
    waiting_for_custom_points = State()
