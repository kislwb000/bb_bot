from aiogram.fsm.state import State, StatesGroup


class EventStates(StatesGroup):
    waiting_for_title = State()
