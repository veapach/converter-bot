from aiogram.fsm.state import State, StatesGroup


class TikTokEditStates(StatesGroup):
    waiting_url = State()
    crop_editing = State()
    time_editing = State()
    preview = State()
    processing = State()