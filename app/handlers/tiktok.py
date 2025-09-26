import os
import re
import asyncio
import tempfile

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.states import TikTokEditStates
from app.config import Config
from app.models import Settings
from app.keyboards.inline import (
    main_menu, back_menu, crop_edit_menu, crop_size_menu, 
    time_edit_menu, preview_menu
)
from app.services.tiktok import TikTokDownloader, VideoEditor
from app.services.converter import Converter
from app.handlers.start import format_main_menu_text

router = Router()

# Регулярное выражение для TikTok URL
TIKTOK_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/.*'
)


async def add_message_for_cleanup(state: FSMContext, message_id: int, chat_id: int):
    """Добавляет сообщение в список для очистки"""
    data = await state.get_data()
    cleanup_messages = data.get("cleanup_messages", [])
    cleanup_messages.append({"message_id": message_id, "chat_id": chat_id})
    await state.update_data(cleanup_messages=cleanup_messages)


async def cleanup_messages(state: FSMContext, bot):
    """Удаляет все сообщения из списка очистки"""
    data = await state.get_data()
    cleanup_messages = data.get("cleanup_messages", [])
    
    for msg_info in cleanup_messages:
        try:
            await bot.delete_message(
                chat_id=msg_info["chat_id"], 
                message_id=msg_info["message_id"]
            )
        except Exception:
            pass
    
    # Очищаем список
    await state.update_data(cleanup_messages=[])


@router.message(F.text)
async def handle_tiktok_url_direct(message: Message, state: FSMContext):
    """Обработка TikTok URL в обычном режиме"""
    if not message.text:
        return
    
    url = message.text.strip()
    
    if not TIKTOK_URL_PATTERN.match(url):
        return  # Не TikTok URL, пропускаем
    
    # Предлагаем открыть редактор
    await message.answer(
        "🎬 Обнаружена ссылка на TikTok!\n\n"
        "Хотите открыть редактор для обрезки и настройки видео?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Открыть редактор", callback_data="tiktok_editor_direct")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="tiktok_back_main")]
        ])
    )
    
    # Сохраняем URL для дальнейшего использования
    await state.update_data(pending_tiktok_url=url)


@router.callback_query(F.data == "tiktok_editor_direct")
async def handle_tiktok_editor_direct(cb: CallbackQuery, state: FSMContext):
    """Обработка прямого перехода к редактору"""
    data = await state.get_data()
    url = data.get("pending_tiktok_url")
    
    if not url:
        await cb.answer("Ошибка: URL не найден")
        return
    
    # Удаляем главное меню если есть
    menu_msg_id = data.get("menu_message_id")
    chat_id = data.get("chat_id") or cb.message.chat.id
    if menu_msg_id and chat_id:
        try:
            await cb.bot.delete_message(chat_id=chat_id, message_id=menu_msg_id)
        except Exception:
            pass
    
    loading_msg = await cb.message.edit_text("⏳ Загружаю видео с TikTok...")
    # Добавляем сообщение в список для очистки
    await add_message_for_cleanup(state, loading_msg.message_id, loading_msg.chat.id)
    
    # Используем тот же код, что и в handle_tiktok_url
    downloader = TikTokDownloader()
    try:
        # Загружаем видео
        video_path = await downloader.download_video(url)
        
        # ... (остальной код как в handle_tiktok_url)
        # Создаем редактор видео
        editor = VideoEditor(video_path)
        video_info = editor.get_video_info()
        
        # Получаем настройки
        settings_data = await state.get_data()
        settings = settings_data.get("settings")
        if not settings:
            settings = Settings.from_defaults(Config.load().defaults)
        
        # Начальные параметры времени
        start_time = 0.0
        duration = min(3.0, video_info["duration"])  # Максимум 3 секунды
        
        # Вычисляем начальную позицию кропа
        crop_x, crop_y, crop_width, crop_height = editor.calculate_crop_bounds(
            settings.width, settings.height
        )
        
        # Создаем превью времени (первый этап)
        crop_params = (crop_x, crop_y, crop_width, crop_height)
        preview_bytes = editor.create_time_preview(start_time, duration, crop_params)
        
        if not preview_bytes:
            await cb.message.edit_text("❌ Ошибка при обработке видео")
            return
        
        # Сохраняем данные в состояние
        await state.update_data(
            video_path=video_path,
            editor=editor,
            downloader=downloader,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height,
            video_info=video_info,
            settings=settings,
            start_time=start_time,
            duration=duration
        )
        
        # Отправляем превью времени
        await cb.message.edit_media(
            InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, "time_preview.jpg"),
                caption=(
                    f"⏰ <b>Выбор временного отрезка</b>\n\n"
                    f"� Общая длительность: {video_info['duration']:.1f}s\n"
                    f"✂️ Выбранный отрезок: {start_time:.1f}s - {start_time + duration:.1f}s\n"
                    f"⏱ Длительность: {duration:.1f}s\n\n"
                    f"📝 <b>Управление:</b>\n"
                    f"⏪⏪ = -1 сек   ⏪ = -0.1 сек\n"
                    f"⏩ = +0.1 сек   ⏩⏩ = +1 сек\n\n"
                    f"Максимальная длительность: 3.0s"
                ),
                parse_mode="HTML"
            ),
            reply_markup=time_edit_menu(start_time, duration, video_info["duration"])
        )
        
        await state.update_data(
            time_message_id=cb.message.message_id,
            chat_id=cb.message.chat.id
        )
        await state.set_state(TikTokEditStates.time_editing)
        
    except Exception as e:
        await cb.message.edit_text(f"❌ Ошибка при загрузке видео: {str(e)}")
        downloader.cleanup()
    
    await cb.answer()


@router.callback_query(F.data == "tiktok_editor")
async def start_tiktok_editor(cb: CallbackQuery, state: FSMContext):
    """Начало работы с TikTok редактором"""
    await cb.message.edit_text(
        "📱 <b>TikTok Редактор</b>\n\n"
        "Отправьте ссылку на TikTok видео для редактирования:",
        reply_markup=back_menu(),
        parse_mode="HTML"
    )
    # Сохраняем ID сообщения для удаления после загрузки
    await state.update_data(
        editor_menu_message_id=cb.message.message_id,
        editor_menu_chat_id=cb.message.chat.id
    )
    await state.set_state(TikTokEditStates.waiting_url)
    await cb.answer()


@router.message(TikTokEditStates.waiting_url)
async def handle_tiktok_url(message: Message, state: FSMContext):
    """Обработка TikTok URL"""
    url = message.text.strip()
    
    if not TIKTOK_URL_PATTERN.match(url):
        await message.answer(
            "❌ Неверная ссылка на TikTok. Пожалуйста, отправьте корректную ссылку."
        )
        return
    
    # Удаляем предыдущие сообщения
    data = await state.get_data()
    
    # Удаляем главное меню если есть
    menu_msg_id = data.get("menu_message_id")
    chat_id = data.get("chat_id") or message.chat.id
    if menu_msg_id and chat_id:
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=menu_msg_id)
        except Exception:
            pass
    
    # Удаляем сообщение редактора
    editor_menu_msg_id = data.get("editor_menu_message_id")
    editor_menu_chat_id = data.get("editor_menu_chat_id") or message.chat.id
    if editor_menu_msg_id and editor_menu_chat_id:
        try:
            await message.bot.delete_message(chat_id=editor_menu_chat_id, message_id=editor_menu_msg_id)
        except Exception:
            pass
    
    status_msg = await message.answer("⏳ Загружаю видео с TikTok...")
    # Добавляем статусное сообщение в список для очистки
    await add_message_for_cleanup(state, status_msg.message_id, status_msg.chat.id)
    
    downloader = TikTokDownloader()
    try:
        # Загружаем видео
        video_path = await downloader.download_video(url)
        
        # Создаем редактор видео
        editor = VideoEditor(video_path)
        video_info = editor.get_video_info()
        
        # Получаем настройки
        settings_data = await state.get_data()
        settings = settings_data.get("settings")
        if not settings:
            settings = Settings.from_defaults(Config.load().defaults)
        
        # Начальные параметры времени
        start_time = 0.0
        duration = min(3.0, video_info["duration"])  # Максимум 3 секунды
        
        # Вычисляем начальную позицию кропа
        crop_x, crop_y, crop_width, crop_height = editor.calculate_crop_bounds(
            settings.width, settings.height
        )
        
        # Создаем превью времени (первый этап)
        crop_params = (crop_x, crop_y, crop_width, crop_height)
        preview_bytes = editor.create_time_preview(start_time, duration, crop_params)
        
        if not preview_bytes:
            await status_msg.edit_text("❌ Ошибка при обработке видео")
            return
        
        # Сохраняем данные в состояние
        await state.update_data(
            video_path=video_path,
            editor=editor,
            downloader=downloader,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height,
            video_info=video_info,
            settings=settings,
            start_time=start_time,
            duration=duration
        )
        
        # Отправляем превью времени
        await status_msg.delete()
        
        time_msg = await message.answer_photo(
            BufferedInputFile(preview_bytes, "time_preview.jpg"),
            caption=(
                f"⏰ <b>Выбор временного отрезка</b>\n\n"
                f"� Общая длительность: {video_info['duration']:.1f}s\n"
                f"✂️ Выбранный отрезок: {start_time:.1f}s - {start_time + duration:.1f}s\n"
                f"⏱ Длительность: {duration:.1f}s\n\n"
                f"📝 <b>Управление:</b>\n"
                f"⏪⏪ = -1 сек   ⏪ = -0.1 сек\n"
                f"⏩ = +0.1 сек   ⏩⏩ = +1 сек\n\n"
                f"Максимальная длительность: 3.0s"
            ),
            reply_markup=time_edit_menu(start_time, duration, video_info["duration"]),
            parse_mode="HTML"
        )
        
        await state.update_data(
            time_message_id=time_msg.message_id,
            chat_id=time_msg.chat.id
        )
        await state.set_state(TikTokEditStates.time_editing)
        
    except Exception as e:
        error_msg = str(e)
        
        # Определяем тип ошибки и показываем понятное сообщение
        if "Requested format is not available" in error_msg:
            await status_msg.edit_text(
                "❌ <b>Видео недоступно для загрузки</b>\n\n"
                "Возможные причины:\n"
                "• Видео приватное или удалено\n"
                "• Региональные ограничения\n"
                "• Ограничения правообладателя\n\n"
                "Попробуйте другое видео.",
                parse_mode="HTML"
            )
        elif "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
            await status_msg.edit_text(
                "❌ <b>Доступ к видео запрещен</b>\n\n"
                "Видео может быть:\n"
                "• Приватным\n"
                "• Заблокированным в вашем регионе\n"
                "• Удаленным автором\n\n"
                "Попробуйте другое видео.",
                parse_mode="HTML"
            )
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            await status_msg.edit_text(
                "❌ <b>Ошибка сети</b>\n\n"
                "Проблемы с подключением к TikTok.\n"
                "Попробуйте еще раз через несколько минут.",
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                f"❌ <b>Ошибка при загрузке видео</b>\n\n"
                f"Детали: {error_msg}\n\n"
                f"Попробуйте другую ссылку или повторите попытку.",
                parse_mode="HTML"
            )
        
        downloader.cleanup()


@router.callback_query(TikTokEditStates.crop_editing, F.data.startswith("crop_move:"))
async def handle_crop_move(cb: CallbackQuery, state: FSMContext):
    """Обработка перемещения кропа"""
    direction = cb.data.split(":")[1]
    data = await state.get_data()
    
    editor: VideoEditor = data["editor"]
    crop_x = data["crop_x"]
    crop_y = data["crop_y"]
    crop_width = data["crop_width"]
    crop_height = data["crop_height"]
    settings = data["settings"]
    
    # Шаг перемещения
    step = 20
    
    # Перемещаем кроп
    if direction == "up":
        crop_y = max(0, crop_y - step)
    elif direction == "down":
        crop_y = min(editor.height - crop_height, crop_y + step)
    elif direction == "left":
        crop_x = max(0, crop_x - step)
    elif direction == "right":
        crop_x = min(editor.width - crop_width, crop_x + step)
    
    # Создаем новое превью
    preview_bytes = editor.create_crop_preview(crop_x, crop_y, crop_width, crop_height)
    
    if preview_bytes:
        # Обновляем сообщение
        try:
            await cb.message.edit_media(
                media=InputMediaPhoto(
                    media=BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                    caption=(
                        f"🎬 <b>Редактирование кропа</b>\n\n"
                        f"📐 Размер видео: {editor.width}x{editor.height}\n"
                        f"⏱ Длительность: {editor.duration:.1f}s\n"
                        f"✂️ Кроп: {crop_width}x{crop_height}\n\n"
                        f"Используйте стрелки для перемещения области обрезки:"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=crop_edit_menu(settings)
            )
        except Exception:
            # Если не удалось обновить медиа, отправляем новое сообщение
            await cb.message.delete()
            new_msg = await cb.message.answer_photo(
                BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                caption=(
                    f"🎬 <b>Редактирование кропа</b>\n\n"
                    f"📐 Размер видео: {editor.width}x{editor.height}\n"
                    f"⏱ Длительность: {editor.duration:.1f}s\n"
                    f"✂️ Кроп: {crop_width}x{crop_height}\n\n"
                    f"Используйте стрелки для перемещения области обрезки:"
                ),
                reply_markup=crop_edit_menu(settings),
                parse_mode="HTML"
            )
            await state.update_data(crop_message_id=new_msg.message_id)
    
    # Сохраняем новые координаты
    await state.update_data(crop_x=crop_x, crop_y=crop_y)
    await cb.answer()


@router.callback_query(TikTokEditStates.crop_editing, F.data == "crop_size")
async def handle_crop_size_menu(cb: CallbackQuery, state: FSMContext):
    """Показ меню выбора размера кропа"""
    await cb.message.edit_reply_markup(reply_markup=crop_size_menu())
    await cb.answer()


@router.callback_query(TikTokEditStates.crop_editing, F.data.startswith("crop_size_set:"))
async def handle_crop_size_set(cb: CallbackQuery, state: FSMContext):
    """Установка размера кропа"""
    size = cb.data.split(":")[1]
    width, height = map(int, size.split("x"))
    
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    settings: Settings = data["settings"]
    
    # Обновляем настройки
    settings.width = width
    settings.height = height
    
    # Пересчитываем позицию кропа
    crop_x, crop_y, crop_width, crop_height = editor.calculate_crop_bounds(width, height)
    
    # Создаем новое превью
    preview_bytes = editor.create_crop_preview(crop_x, crop_y, crop_width, crop_height)
    
    if preview_bytes:
        try:
            await cb.message.edit_media(
                media=InputMediaPhoto(
                    media=BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                    caption=(
                        f"🎬 <b>Редактирование кропа</b>\n\n"
                        f"📐 Размер видео: {editor.width}x{editor.height}\n"
                        f"⏱ Длительность: {editor.duration:.1f}s\n"
                        f"✂️ Кроп: {crop_width}x{crop_height}\n\n"
                        f"Используйте стрелки для перемещения области обрезки:"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=crop_edit_menu(settings)
            )
        except Exception:
            await cb.message.delete()
            new_msg = await cb.message.answer_photo(
                BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                caption=(
                    f"🎬 <b>Редактирование кропа</b>\n\n"
                    f"📐 Размер видео: {editor.width}x{editor.height}\n"
                    f"⏱ Длительность: {editor.duration:.1f}s\n"
                    f"✂️ Кроп: {crop_width}x{crop_height}\n\n"
                    f"Используйте стрелки для перемещения области обрезки:"
                ),
                reply_markup=crop_edit_menu(settings),
                parse_mode="HTML"
            )
            await state.update_data(crop_message_id=new_msg.message_id)
    
    # Сохраняем новые параметры
    await state.update_data(
        settings=settings,
        crop_x=crop_x,
        crop_y=crop_y,
        crop_width=crop_width,
        crop_height=crop_height
    )
    await cb.answer()


@router.callback_query(TikTokEditStates.crop_editing, F.data == "crop_back")
async def handle_crop_back(cb: CallbackQuery, state: FSMContext):
    """Возврат к редактированию кропа"""
    data = await state.get_data()
    settings = data["settings"]
    await cb.message.edit_reply_markup(reply_markup=crop_edit_menu(settings))
    await cb.answer()


@router.callback_query(TikTokEditStates.crop_editing, F.data == "crop_back_to_main")
async def handle_crop_back_to_main(cb: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из редактирования кропа"""
    data = await state.get_data()
    settings = data.get("settings")
    
    # Очищаем временные данные
    downloader: TikTokDownloader = data.get("downloader")
    if downloader:
        downloader.cleanup()
    
    # Очищаем сообщение редактора TikTok
    editor_menu_message_id = data.get("editor_menu_message_id")
    editor_menu_chat_id = data.get("editor_menu_chat_id")
    if editor_menu_message_id and editor_menu_chat_id:
        try:
            await cb.bot.delete_message(editor_menu_chat_id, editor_menu_message_id)
        except Exception:
            pass
    
    # Очищаем все служебные сообщения
    await cleanup_messages(state, cb.bot)
    
    await cb.message.delete()
    
    if settings:
        new_menu = await cb.message.answer(
            format_main_menu_text(settings),
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        await state.update_data(
            menu_message_id=new_menu.message_id,
            chat_id=new_menu.chat.id
        )
    
    await state.clear()
    await cb.answer()


@router.callback_query(F.data == "tiktok_back_main")
async def handle_tiktok_back_to_main(cb: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из TikTok редактора"""
    data = await state.get_data()
    settings = data.get("settings")
    
    # Очищаем временные данные
    downloader: TikTokDownloader = data.get("downloader")
    if downloader:
        downloader.cleanup()
        
    # Очищаем временные файлы если они есть (от процесса сжатия)
    oversized_file_path = data.get("oversized_file_path")
    temp_dir = data.get("temp_dir_path")
    if oversized_file_path and os.path.exists(oversized_file_path):
        try:
            os.remove(oversized_file_path)
        except Exception:
            pass
    if temp_dir and os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
    
    # Очищаем сообщение редактора TikTok
    editor_menu_message_id = data.get("editor_menu_message_id")
    editor_menu_chat_id = data.get("editor_menu_chat_id")
    if editor_menu_message_id and editor_menu_chat_id:
        try:
            await cb.bot.delete_message(editor_menu_chat_id, editor_menu_message_id)
        except Exception:
            pass
    
    # Очищаем все служебные сообщения
    await cleanup_messages(state, cb.bot)
    
    # Изменяем текущее сообщение на главное меню вместо удаления
    if settings:
        await cb.message.edit_text(
            format_main_menu_text(settings),
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        await state.update_data(
            menu_message_id=cb.message.message_id,
            chat_id=cb.message.chat.id
        )
    
    await state.clear()
    await cb.answer()


@router.callback_query(TikTokEditStates.crop_editing, F.data == "crop_next")
async def handle_crop_next(cb: CallbackQuery, state: FSMContext):
    """Переход к предпросмотру"""
    await show_preview(cb, state)
    await cb.answer()

@router.callback_query(TikTokEditStates.time_editing, F.data == "ignore")
async def handle_time_ignore(cb: CallbackQuery, state: FSMContext):
    """Обработка игнорируемой кнопки"""
    await cb.answer("Ниже кнопки для управления временем")

@router.callback_query(TikTokEditStates.time_editing, F.data.startswith("time_"))
async def handle_time_edit(cb: CallbackQuery, state: FSMContext):
    """Обработка редактирования времени"""
    action = cb.data.split(":")[0]
    direction = cb.data.split(":")[1] if ":" in cb.data else None
    
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    video_info = data["video_info"]
    start_time = data.get("start_time", 0.0)
    duration = data.get("duration", min(3.0, video_info.get("duration", 3.0)))
    max_duration = min(3.0, video_info.get("duration", 3.0))
    
    # Определяем шаг в зависимости от типа кнопки
    if direction and direction.endswith("_fast"):
        step = 1.0  # Быстрый шаг - 1 секунда
        direction = direction.replace("_fast", "")  # Убираем суффикс
    else:
        step = 0.1  # Обычный шаг - 0.1 секунды
    
    if action == "time_start":
        if direction == "left":
            start_time = max(0, start_time - step)
        elif direction == "right":
            start_time = min(video_info["duration"] - duration, start_time + step)
    
    elif action == "time_end":
        if direction == "left":
            new_duration = max(0.1, duration - step)
            if start_time + new_duration <= video_info["duration"]:
                duration = new_duration
        elif direction == "right":
            new_duration = min(max_duration, duration + step)
            if start_time + new_duration <= video_info["duration"]:
                duration = new_duration
    
    elif action == "time_back":
        # Возврат к редактированию кропа
        crop_params = (data["crop_x"], data["crop_y"], data["crop_width"], data["crop_height"])
        preview_bytes = editor.create_crop_preview(*crop_params)
        
        if preview_bytes:
            try:
                media = InputMediaPhoto(
                    media=BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                    caption=(
                        f"🎬 <b>Редактирование кропа</b>\n\n"
                        f"📐 Размер видео: {editor.width}x{editor.height}\n"
                        f"⏱ Длительность: {editor.duration:.1f}s\n"
                        f"✂️ Кроп: {data['crop_width']}x{data['crop_height']}\n\n"
                        f"Используйте стрелки для перемещения области обрезки:"
                    ),
                    parse_mode="HTML"
                )
                await cb.message.edit_media(
                    media=media,
                    reply_markup=crop_edit_menu(data["settings"])
                )
            except Exception:
                pass
        
        await state.set_state(TikTokEditStates.crop_editing)
        await cb.answer()
        return
    
    elif action == "time_done":
        # Переходим к редактированию кропа
        await show_crop_editing(cb, state)
        return
    
    elif action == "time_info":
        await cb.answer(f"Отрезок: {start_time:.1f}s - {start_time + duration:.1f}s")
        return
    
    # Обновляем превью
    crop_params = (data["crop_x"], data["crop_y"], data["crop_width"], data["crop_height"])
    preview_bytes = editor.create_time_preview(start_time, duration, crop_params)
    
    if preview_bytes:
        try:
            media = InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, "time_preview.jpg"),
                caption=(
                    f"⏰ <b>Выбор временного отрезка</b>\n\n"
                    f"📹 Общая длительность: {video_info['duration']:.1f}s\n"
                    f"✂️ Выбранный отрезок: {start_time:.1f}s - {start_time + duration:.1f}s\n"
                    f"⏱ Длительность: {duration:.1f}s\n\n"
                    f"📝 <b>Управление:</b>\n"
                    f"⏪⏪ = -1 сек   ⏪ = -0.1 сек\n"
                    f"⏩ = +0.1 сек   ⏩⏩ = +1 сек\n\n"
                    f"Максимальная длительность: 3.0s"
                ),
                parse_mode="HTML"
            )
            await cb.message.edit_media(
                media=media,
                reply_markup=time_edit_menu(start_time, duration, video_info["duration"])
            )
        except Exception:
            pass
    
    await state.update_data(start_time=start_time, duration=duration)
    await cb.answer()


async def show_crop_editing(cb: CallbackQuery, state: FSMContext):
    """Показать интерфейс редактирования кропа"""
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    settings = data["settings"]
    crop_params = (data["crop_x"], data["crop_y"], data["crop_width"], data["crop_height"])
    
    preview_bytes = editor.create_crop_preview(*crop_params)
    
    if preview_bytes:
        await cb.message.edit_media(
            InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                caption=(
                    f"🎬 <b>Редактирование кропа</b>\n\n"
                    f"📐 Размер видео: {editor.width}x{editor.height}\n"
                    f"⏱ Длительность: {editor.duration:.1f}s\n"
                    f"✂️ Кроп: {data['crop_width']}x{data['crop_height']}\n\n"
                    f"Используйте стрелки для перемещения области обрезки:"
                ),
                parse_mode="HTML"
            ),
            reply_markup=crop_edit_menu(settings)
        )
        
        await state.update_data(
            crop_message_id=cb.message.message_id,
            chat_id=cb.message.chat.id
        )
        await state.set_state(TikTokEditStates.crop_editing)


async def show_preview(cb: CallbackQuery, state: FSMContext):
    """Показывает предпросмотр результата"""
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    
    crop_x = data["crop_x"]
    crop_y = data["crop_y"]  
    crop_width = data["crop_width"]
    crop_height = data["crop_height"]
    
    # Обеспечиваем наличие параметров времени
    video_info = data.get("video_info", {})
    start_time = data.get("start_time", 0.0)
    duration = data.get("duration", min(3.0, video_info.get("duration", 3.0)))
    
    # Сохраняем параметры времени, если их не было
    if "start_time" not in data or "duration" not in data:
        await state.update_data(start_time=start_time, duration=duration)
    
    settings: Settings = data["settings"]
    
    # Создаем превью
    await cb.message.delete()
    preview_msg = await cb.message.answer("🎬 Создаю предпросмотр...")
    await add_message_for_cleanup(state, preview_msg.message_id, preview_msg.chat.id)
    
    try:
        # Временный файл для превью
        temp_dir = tempfile.mkdtemp(prefix="preview_")
        preview_path = os.path.join(temp_dir, "preview.mp4")
        
        crop_params = (crop_x, crop_y, crop_width, crop_height)
        success = await editor.create_video_preview(start_time, duration, crop_params, preview_path)
        
        if success:
            await preview_msg.edit_text("📱 Предпросмотр результата:")
            # Добавляем сообщение предпросмотра в список для очистки
            await add_message_for_cleanup(state, preview_msg.message_id, preview_msg.chat.id)
            
            video_msg = await preview_msg.answer_video(
                FSInputFile(preview_path),
                caption=(
                    f"🎬 <b>Предпросмотр</b>\n\n"
                    f"📐 Размер: {crop_width}x{crop_height} → {settings.width}x{settings.height}\n"
                    f"⏰ Время: {start_time:.1f}s - {start_time + duration:.1f}s\n"
                    f"⏱ Длительность: {duration:.1f}s\n\n"
                    f"Выберите действие:"
                ),
                reply_markup=preview_menu(),
                parse_mode="HTML"
            )
            # Добавляем видео с превью в список для очистки
            await add_message_for_cleanup(state, video_msg.message_id, video_msg.chat.id)
            
            # Очистка
            try:
                os.remove(preview_path)
                os.rmdir(temp_dir)
            except Exception:
                pass
        else:
            await preview_msg.edit_text("❌ Ошибка создания предпросмотра")
            
    except Exception as e:
        await preview_msg.edit_text(f"❌ Ошибка: {str(e)}")
    
    await state.set_state(TikTokEditStates.preview)
    await cb.answer()


# Обработчики для предпросмотра
@router.callback_query(TikTokEditStates.preview, F.data == "preview_convert")
async def handle_preview_convert(cb: CallbackQuery, state: FSMContext):
    """Начинаем конвертацию после подтверждения"""
    await start_video_processing(cb, state)


@router.callback_query(TikTokEditStates.preview, F.data == "preview_edit_crop")
async def handle_preview_edit_crop(cb: CallbackQuery, state: FSMContext):
    """Возврат к редактированию кропа"""
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    settings = data["settings"]
    crop_params = (data["crop_x"], data["crop_y"], data["crop_width"], data["crop_height"])
    
    preview_bytes = editor.create_crop_preview(*crop_params)
    
    if preview_bytes:
        # Изменяем текущее сообщение на кроп-редактор
        await cb.message.edit_media(
            InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, "crop_preview.jpg"),
                caption=(
                    f"🎬 <b>Редактирование кропа</b>\n\n"
                    f"📐 Размер видео: {editor.width}x{editor.height}\n"
                    f"⏱ Длительность: {editor.duration:.1f}s\n"
                    f"✂️ Кроп: {data['crop_width']}x{data['crop_height']}\n\n"
                    f"Используйте стрелки для перемещения области обрезки:"
                ),
                parse_mode="HTML"
            ),
            reply_markup=crop_edit_menu(settings)
        )
        
        await state.update_data(
            crop_message_id=cb.message.message_id,
            chat_id=cb.message.chat.id
        )
        await state.set_state(TikTokEditStates.crop_editing)
    
    await cb.answer()


@router.callback_query(TikTokEditStates.preview, F.data == "preview_edit_time")
async def handle_preview_edit_time(cb: CallbackQuery, state: FSMContext):
    """Возврат к редактированию времени"""
    data = await state.get_data()
    editor: VideoEditor = data["editor"]
    video_info = data["video_info"]
    start_time = data.get("start_time", 0.0)
    duration = data.get("duration", min(3.0, video_info.get("duration", 3.0)))
    
    crop_params = (data["crop_x"], data["crop_y"], data["crop_width"], data["crop_height"])
    preview_bytes = editor.create_time_preview(start_time, duration, crop_params)
    
    if preview_bytes:
        # Изменяем текущее сообщение на редактор времени
        await cb.message.edit_media(
            InputMediaPhoto(
                media=BufferedInputFile(preview_bytes, "time_preview.jpg"),
                caption=(
                    f"⏰ <b>Выбор временного отрезка</b>\n\n"
                    f"📹 Общая длительность: {video_info['duration']:.1f}s\n"
                    f"✂️ Выбранный отрезок: {start_time:.1f}s - {start_time + duration:.1f}s\n"
                    f"⏱ Длительность: {duration:.1f}s\n\n"
                    f"📝 <b>Управление:</b>\n"
                    f"⏪⏪ = -1 сек   ⏪ = -0.1 сек\n"
                    f"⏩ = +0.1 сек   ⏩⏩ = +1 сек\n\n"
                    f"Максимальная длительность: 3.0s"
                ),
                parse_mode="HTML"
            ),
            reply_markup=time_edit_menu(start_time, duration, video_info["duration"])
        )
        
        await state.update_data(crop_message_id=cb.message.message_id)
        await state.set_state(TikTokEditStates.time_editing)
    
    await cb.answer()


@router.callback_query(F.data == "compress_file")
async def handle_compress_file(cb: CallbackQuery, state: FSMContext):
    """Обработка сжатия файла"""
    data = await state.get_data()
    oversized_file_path = data.get("oversized_file_path")
    temp_dir = data.get("temp_dir_path")
    
    # Убираем флаг ожидания выбора
    await state.update_data(awaiting_compression_choice=False)
    
    if not oversized_file_path or not os.path.exists(oversized_file_path):
        await cb.message.edit_text("❌ Файл не найден")
        return
        
    processing_msg = await cb.message.edit_text("🗜 Сжимаю файл...")
    
    try:
        # Получаем параметры из состояния
        settings: Settings = data["settings"]
        crop_x = data["crop_x"]
        crop_y = data["crop_y"]
        crop_width = data["crop_width"]
        crop_height = data["crop_height"]
        start_time = data["start_time"]
        duration = data["duration"]
        video_path = data["video_path"]
        
        from app.services.converter import Converter
        converter = Converter()
        
        # Попытки сжатия с разными параметрами
        compression_attempts = [
            {"crf": 35, "bitrate": "500k"},    # Первая попытка
            {"crf": 40, "bitrate": "300k"},    # Вторая попытка  
            {"crf": 45, "bitrate": "200k"},    # Третья попытка
            {"crf": 50, "bitrate": "150k"},    # Четвертая попытка
        ]
        
        compressed_path = None
        for attempt_num, params in enumerate(compression_attempts, 1):
            await processing_msg.edit_text(f"🗜 Сжимаю файл... Попытка {attempt_num}/4")
            
            compressed_path = os.path.join(temp_dir, f"compressed_{attempt_num}.webm")
            
            # Формируем команду FFmpeg с дополнительным сжатием
            ffmpeg_path = converter.ffmpeg
            cmd = [
                ffmpeg_path,
                "-y",
                "-ss", str(start_time),
                "-t", str(duration),
                "-i", video_path,
                "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale={settings.width}:{settings.height}:flags=lanczos",
                "-r", str(settings.fps),
                "-c:v", "libvpx-vp9",
                "-crf", str(params["crf"]),
                "-b:v", params["bitrate"],
                "-c:a", "libopus" if settings.audio else "copy",
                "-b:a", "64k" if settings.audio else "0",
                "-an" if not settings.audio else "",
                compressed_path
            ]
            
            # Удаляем пустые элементы
            cmd = [x for x in cmd if x]
            
            # Запускаем сжатие
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(compressed_path):
                file_size = os.path.getsize(compressed_path)
                if file_size <= 256 * 1024:  # Успешно сжали до нужного размера
                    # Отправляем сжатый файл
                    await processing_msg.edit_text("✅ Готово! Отправляю сжатый файл...")
                    
                    await processing_msg.answer_document(
                        FSInputFile(compressed_path),
                        caption=f"📱 TikTok видео (сжатое)\n"
                               f"📐 {settings.width}x{settings.height}\n"
                               f"⏱ {duration:.1f}s\n"
                               f"📦 {file_size // 1024} KB"
                    )
                    
                    # Очистка всех файлов
                    try:
                        if os.path.exists(oversized_file_path):
                            os.remove(oversized_file_path)
                        if os.path.exists(compressed_path):
                            os.remove(compressed_path)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
                    except Exception:
                        pass
                    
                    # Очищаем все сообщения и возвращаемся в главное меню
                    await cleanup_messages(state, cb.bot)
                    await return_to_main_menu(state, cb)
                    return
            
            # Удаляем неудачную попытку
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
        
        # Если не удалось сжать до нужного размера
        await processing_msg.edit_text(
            "❌ <b>Не получилось уменьшить файл</b>\n\n"
            "Попробованы разные способы сжатия, но файл всё ещё слишком большой.\n\n"
            "💡 <b>Рекомендации:</b>\n"
            "• Уменьшите длительность видео\n" 
            "• Выберите меньшее разрешение\n"
            "• Отключите звук, если он не нужен",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="tiktok_back_main")]
            ]),
            parse_mode="HTML"
        )
        
        # Очистка файлов
        try:
            if os.path.exists(oversized_file_path):
                os.remove(oversized_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception:
            pass
            
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ Ошибка при сжатии: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="tiktok_back_main")]
            ])
        )


async def return_to_main_menu(state: FSMContext, message_or_callback):
    """Возврат в главное меню"""
    data = await state.get_data()
    settings = data.get("settings")
    
    # Очищаем временные данные
    downloader: TikTokDownloader = data.get("downloader")
    if downloader:
        downloader.cleanup()
    
    if settings:
        # Определяем, что нам передали - message или callback
        if hasattr(message_or_callback, 'message'):
            # Это callback
            chat_id = message_or_callback.message.chat.id
            bot = message_or_callback.bot
        else:
            # Это message
            chat_id = message_or_callback.chat.id
            bot = message_or_callback.bot
        
        try:
            new_menu = await bot.send_message(
                chat_id,
                format_main_menu_text(settings),
                reply_markup=main_menu(),
                parse_mode="HTML"
            )
            await state.update_data(
                menu_message_id=new_menu.message_id,
                chat_id=new_menu.chat.id
            )
        except Exception:
            pass
    
    await state.clear()


async def start_video_processing(cb: CallbackQuery, state: FSMContext):
    """Начинает обработку видео"""
    data = await state.get_data()
    
    # Заменяем фото на текстовое сообщение о процессе
    await cb.message.delete()
    processing_msg = await cb.message.answer("🔄 Обрабатываю видео...")
    await state.set_state(TikTokEditStates.processing)
    
    try:
        # Получаем все параметры
        video_path = data["video_path"]
        downloader: TikTokDownloader = data["downloader"]
        settings: Settings = data["settings"]
        
        crop_x = data["crop_x"]
        crop_y = data["crop_y"]
        crop_width = data["crop_width"]
        crop_height = data["crop_height"]
        start_time = data["start_time"]
        duration = data["duration"]
        
        # Создаем конвертер
        converter = Converter()
        
        # Временный файл для результата
        temp_dir = tempfile.mkdtemp(prefix="tiktok_result_")
        output_path = os.path.join(temp_dir, "result.webm")
        
        # Формируем команду FFmpeg с кропом и обрезкой по времени
        ffmpeg_path = converter.ffmpeg
        
        cmd = [
            ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", video_path,
            "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},scale={settings.width}:{settings.height}:flags=lanczos",
            "-r", str(settings.fps),
        ]
        
        if settings.audio:
            cmd.extend(["-c:a", "libopus", "-b:a", "96k"])
        else:
            cmd.append("-an")
        
        cmd.extend([
            "-c:v", settings.codec,
            "-crf", str(settings.crf),
            "-b:v", "0",
            "-pix_fmt", "yuv420p",
            "-deadline", settings.preset,
            output_path
        ])
        
        # Запускаем конвертацию
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_text = stderr.decode('utf-8', errors='ignore')
            await processing_msg.edit_text(f"❌ Ошибка при обработке видео:\n{error_text}")
            return
        
        # Проверяем размер файла
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 256 * 1024:  # 256 KB
                # Сохраняем путь к файлу для повторной обработки
                await state.update_data(
                    oversized_file_path=output_path, 
                    temp_dir_path=temp_dir,
                    awaiting_compression_choice=True  # Флаг ожидания выбора пользователя
                )
                
                await processing_msg.edit_text(
                    f"⚠️ <b>Файл слишком большой</b>\n\n"
                    f"📦 Размер: {file_size // 1024} KB\n"
                    f"📏 Лимит: 256 KB\n\n"
                    f"Что делать?",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🗜 Уменьшить объем", callback_data="compress_file")],
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="tiktok_back_main")]
                    ]),
                    parse_mode="HTML"
                )
                return
            
            # Отправляем результат
            await processing_msg.edit_text("✅ Готово! Отправляю файл...")
            
            await processing_msg.answer_document(
                FSInputFile(output_path),
                caption=f"📱 TikTok видео\n"
                       f"📐 {settings.width}x{settings.height}\n"
                       f"⏱ {duration:.1f}s\n"
                       f"📦 {file_size // 1024} KB"
            )
            
            # Очистка файлов
            try:
                os.remove(output_path)
                os.rmdir(temp_dir)
            except Exception:
                pass
            
            # Очищаем все сообщения и возвращаемся в главное меню
            await cleanup_messages(state, cb.bot)
            await return_to_main_menu(state, cb)
            return
        else:
            await processing_msg.edit_text("❌ Ошибка: выходной файл не создан")
    
    except Exception as e:
        await processing_msg.edit_text(f"❌ Ошибка при обработке: {str(e)}")
    
    finally:
        # Проверяем, не ожидаем ли мы выбор пользователя по сжатию
        data = await state.get_data()
        if data.get("awaiting_compression_choice"):
            return  # Не очищаем данные, пользователь должен сделать выбор
        
        # Очистка и возврат в главное меню
        downloader: TikTokDownloader = data.get("downloader")
        if downloader:
            downloader.cleanup()
        
        # Очищаем сообщение редактора TikTok
        editor_menu_message_id = data.get("editor_menu_message_id")
        editor_menu_chat_id = data.get("editor_menu_chat_id")
        if editor_menu_message_id and editor_menu_chat_id:
            try:
                await processing_msg.bot.delete_message(editor_menu_chat_id, editor_menu_message_id)
            except Exception:
                pass
        
        # Очищаем все служебные сообщения
        await cleanup_messages(state, processing_msg.bot)
        
        settings = data.get("settings")
        if settings:
            new_menu = await processing_msg.answer(
                format_main_menu_text(settings),
                reply_markup=main_menu(),
                parse_mode="HTML"
            )
            await state.update_data(
                menu_message_id=new_menu.message_id,
                chat_id=new_menu.chat.id
            )
        
        await state.clear()
        await cb.answer()