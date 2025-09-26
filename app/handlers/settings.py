from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.keyboards.inline import settings_menu, size_menu, fps_menu, crf_menu
from app.config import Config
from app.models import Settings

router = Router()


@router.callback_query(F.data == "settings")
async def open_settings(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    settings = data.get("settings")
    if not settings:
        settings = Settings.from_defaults(Config.load().defaults)
        await state.update_data(settings=settings)
    await cb.message.edit_text("Настройки конвертации", reply_markup=settings_menu(settings))
    await cb.answer()


@router.callback_query(F.data == "set_size")
async def choose_size(cb: CallbackQuery):
    await cb.message.edit_text("Выберите размер", reply_markup=size_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("size:"))
async def set_size(cb: CallbackQuery, state: FSMContext):
    w, h = map(int, cb.data.split(":")[1].split("x"))
    data = await state.get_data()
    s = data.get("settings")
    s.width, s.height = w, h
    await state.update_data(settings=s)
    await open_settings(cb, state)


@router.callback_query(F.data == "set_fps")
async def choose_fps(cb: CallbackQuery):
    await cb.message.edit_text("Выберите FPS", reply_markup=fps_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("fps:"))
async def set_fps(cb: CallbackQuery, state: FSMContext):
    fps = int(cb.data.split(":")[1])
    data = await state.get_data()
    s = data.get("settings")
    s.fps = fps
    await state.update_data(settings=s)
    await open_settings(cb, state)


@router.callback_query(F.data == "toggle_audio")
async def toggle_audio(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    s = data.get("settings")
    s.audio = not s.audio
    await state.update_data(settings=s)
    await open_settings(cb, state)


@router.callback_query(F.data == "set_crf")
async def choose_crf(cb: CallbackQuery):
    await cb.message.edit_text("Выберите CRF", reply_markup=crf_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("crf:"))
async def set_crf(cb: CallbackQuery, state: FSMContext):
    crf = int(cb.data.split(":")[1])
    data = await state.get_data()
    s = data.get("settings")
    s.crf = crf
    await state.update_data(settings=s)
    await open_settings(cb, state)
