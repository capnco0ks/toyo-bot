from aiogram.fsm.state import State, StatesGroup


class ManualQuantityState(StatesGroup):
    waiting_for_quantity = State()
