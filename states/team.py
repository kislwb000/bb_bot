from aiogram.fsm.state import State, StatesGroup


class TeamStates(StatesGroup):
    waiting_for_event_title = State()
    waiting_for_team_name = State()
