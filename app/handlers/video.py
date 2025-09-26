import os
import asyncio
import tempfile

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from app.config import Config
from app.keyboards.inline import main_menu, back_menu, cancel_menu
from app.models import Settings
from app.services.converter import Converter, FFmpegError
from app.handlers.start import format_main_menu_text

router = Router()


@router.callback_query(F.data == "convert")
async def open_convert(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "Отправьте видео файлом. По окончании конвертации я пришлю webm.", reply_markup=back_menu()
    )
    await state.update_data(menu_message_id=cb.message.message_id, chat_id=cb.message.chat.id)
    await cb.answer()


@router.message(F.video | F.document)
async def handle_video(message: Message, state: FSMContext):
    file = message.video or message.document
    if not file:
        return
    if hasattr(file, "mime_type") and file.mime_type and not file.mime_type.startswith("video"):
        await message.answer("Пожалуйста, пришлите видеофайл.")
        return

    bot = message.bot
    with tempfile.TemporaryDirectory(prefix="dl_") as td:
        name = getattr(file, "file_name", None) or "video.bin"
        in_path = os.path.join(td, name)
        await bot.download(file, in_path)

        data = await state.get_data()
        settings: Settings = data.get("settings")
        if not settings:
            settings = Settings.from_defaults(Config.load().defaults)

        data = await state.get_data()
        menu_msg_id = data.get("menu_message_id")
        chat_id = data.get("chat_id") or message.chat.id
        
        if menu_msg_id and chat_id:
            try:
                await message.bot.delete_message(chat_id=chat_id, message_id=menu_msg_id)
            except Exception:
                pass
        else:
            for msg_id in range(message.message_id - 1, max(0, message.message_id - 10), -1):
                try:
                    await message.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    break
                except Exception:
                    continue

        conv = Converter()
        status = await message.answer("Конвертирую…", reply_markup=cancel_menu())
        loading_frames = [
            "Конвертирую ⠋",
            "Конвертирую ⠙",
            "Конвертирую ⠹",
            "Конвертирую ⠸",
            "Конвертирую ⠼",
            "Конвертирую ⠴",
            "Конвертирую ⠦",
            "Конвертирую ⠧",
            "Конвертирую ⠇",
            "Конвертирую ⠏",
        ]

        async def run_convert():
            return await conv.convert(in_path, settings)

        async def animate_loading(task):
            i = 0
            try:
                while not task.done():
                    await status.edit_text(loading_frames[i % len(loading_frames)])
                    i += 1
                    await asyncio.sleep(0.4)
            except Exception:
                pass

        convert_task = asyncio.create_task(run_convert())
        anim_task = asyncio.create_task(animate_loading(convert_task))
        await state.update_data(
            convert_task=convert_task,
            status_message_id=status.message_id,
            status_chat_id=message.chat.id,
        )
        try:
            out_path = await convert_task
        except FFmpegError as e:
            try:
                await status.edit_text(str(e))
            except Exception:
                pass
            try:
                anim_task.cancel()
            except Exception:
                pass
            new_menu = await message.answer(format_main_menu_text(settings), reply_markup=main_menu(), parse_mode="HTML")
            await state.update_data(menu_message_id=new_menu.message_id, chat_id=new_menu.chat.id, convert_task=None)
            return
        finally:
            try:
                anim_task.cancel()
            except Exception:
                pass

        await status.edit_text("Готово! Отправляю файл…")
        await message.answer_document(
            FSInputFile(out_path), caption=f"{settings.width}x{settings.height} {settings.fps}fps webm"
        )
        try:
            os.remove(out_path)
        except Exception:
            pass
        await status.delete()

        new_menu = await message.answer(format_main_menu_text(settings), reply_markup=main_menu(), parse_mode="HTML")
        await state.update_data(menu_message_id=new_menu.message_id, chat_id=new_menu.chat.id, convert_task=None)


@router.callback_query(F.data == "cancel_convert")
async def cancel_convert(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task: asyncio.Task | None = data.get("convert_task")
    if task and not task.done():
        task.cancel()
    try:
        await cb.message.edit_text("Отмена…")
    except Exception:
        pass
    await cb.answer("Конвертация отменена")
    await state.update_data(convert_task=None)
