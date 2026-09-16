from aiogram.fsm.state import State, StatesGroup


class ProfileSetupState(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_company = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_address = State()


class ProfileEditSingleState(StatesGroup):
    waiting_for_field_value = State()
