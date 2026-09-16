from aiogram.fsm.state import State, StatesGroup


class EditPriceState(StatesGroup):
    waiting_for_price = State()


class AddProductState(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_viscosity = State()
    waiting_for_volume = State()
    waiting_for_package = State()
    waiting_for_article = State()
    waiting_for_description = State()
    waiting_for_photo = State()
