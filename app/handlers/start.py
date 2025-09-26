from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.config import Config
from app.keyboards.inline import main_menu
from app.models import Settings

router = Router()


def format_main_menu_text(settings: Settings) -> str:
    audio_status = "🔊 Вкл" if settings.audio else "🔇 Выкл"
    return f"""🎬 <b>Видео конвертер</b>

📏 <b>Размер:</b> {settings.width}×{settings.height}
🎞️ <b>FPS:</b> {settings.fps}
{audio_status} <b>Аудио:</b> {"Вкл" if settings.audio else "Выкл"}
⚙️ <b>Качество (CRF):</b> {settings.crf}

Отправьте видео/ссылку на TikTok или выберите действие ⬇️"""


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    cfg = Config.load()
    settings = Settings.from_defaults(cfg.defaults)
    await state.update_data(settings=settings)
    msg = await message.answer(
        "⌛", reply_markup=ReplyKeyboardRemove(remove_keyboard=True)
    )
    await msg.delete()
    menu_msg = await message.answer(
        format_main_menu_text(settings), reply_markup=main_menu(), parse_mode="HTML"
    )
    await state.update_data(
        menu_message_id=menu_msg.message_id, chat_id=menu_msg.chat.id
    )


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Проверяем, есть ли активные данные TikTok редактора для очистки
    from app.services.tiktok import TikTokDownloader

    downloader: TikTokDownloader = data.get("downloader")
    if downloader:
        downloader.cleanup()

    # Очищаем сообщение редактора TikTok, если есть
    editor_menu_message_id = data.get("editor_menu_message_id")
    editor_menu_chat_id = data.get("editor_menu_chat_id")
    if editor_menu_message_id and editor_menu_chat_id:
        try:
            await cb.bot.delete_message(editor_menu_chat_id, editor_menu_message_id)
        except Exception:
            pass

    settings = data.get("settings")
    if not settings:
        settings = Settings.from_defaults(Config.load().defaults)
        await state.update_data(settings=settings)
    await cb.message.edit_text(
        format_main_menu_text(settings), reply_markup=main_menu(), parse_mode="HTML"
    )
    await state.update_data(
        menu_message_id=cb.message.message_id, chat_id=cb.message.chat.id
    )
    await state.clear()  # Очищаем состояние при возврате в главное меню
    await cb.answer()
