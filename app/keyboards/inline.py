from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎬 Конвертировать видео", callback_data="convert")],
        [InlineKeyboardButton(text="📱 TikTok редактор", callback_data="tiktok_editor")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def settings_menu(settings) -> InlineKeyboardMarkup:
    audio_label = "вкл" if settings.audio else "выкл"
    kb = [
        [InlineKeyboardButton(text=f"Размер: {settings.width}x{settings.height}", callback_data="set_size")],
        [InlineKeyboardButton(text=f"FPS: {settings.fps}", callback_data="set_fps")],
        [InlineKeyboardButton(text=f"Аудио: {audio_label}", callback_data="toggle_audio")],
        [InlineKeyboardButton(text=f"Качество (CRF): {settings.crf}", callback_data="set_crf")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def back_menu() -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text="Назад", callback_data="back_main")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def cancel_menu() -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel_convert")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def size_menu() -> InlineKeyboardMarkup:
    sizes = ["512x512", "640x640", "720x720", "1080x1080"]
    rows = [[InlineKeyboardButton(text=s, callback_data=f"size:{s}")] for s in sizes]
    rows.append([InlineKeyboardButton(text="Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fps_menu() -> InlineKeyboardMarkup:
    fps_values = ["24", "25", "30", "48", "60"]
    rows = [[InlineKeyboardButton(text=f, callback_data=f"fps:{f}")] for f in fps_values]
    rows.append([InlineKeyboardButton(text="Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def crf_menu() -> InlineKeyboardMarkup:
    values = ["28", "30", "32", "34", "36", "40"]
    rows = [[InlineKeyboardButton(text=v, callback_data=f"crf:{v}")] for v in values]
    rows.append([InlineKeyboardButton(text="Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def crop_edit_menu(settings) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования кропа"""
    kb = [
        [
            InlineKeyboardButton(text="⬆️", callback_data="crop_move:up"),
        ],
        [
            InlineKeyboardButton(text="⬅️", callback_data="crop_move:left"),
            InlineKeyboardButton(text="➡️", callback_data="crop_move:right"),
        ],
        [
            InlineKeyboardButton(text="⬇️", callback_data="crop_move:down"),
        ],
        [
            InlineKeyboardButton(text=f"Размер: {settings.width}x{settings.height}", callback_data="crop_size"),
        ],
        [
            InlineKeyboardButton(text="✅ Далее", callback_data="crop_next"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="crop_back_to_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def crop_size_menu() -> InlineKeyboardMarkup:
    """Клавиатура выбора размера кропа"""
    sizes = ["512x512", "640x640", "720x720", "480x480"]
    rows = [[InlineKeyboardButton(text=s, callback_data=f"crop_size_set:{s}")] for s in sizes]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="crop_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def time_edit_menu(start_time: float, duration: float, max_duration: float) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования временного отрезка"""
    kb = [
        [
            InlineKeyboardButton(text="Начало отрезка", callback_data="ignore"),
        ],
        [
            InlineKeyboardButton(text="⏪⏪", callback_data="time_start:left_fast"),
            InlineKeyboardButton(text="⏪", callback_data="time_start:left"),
            InlineKeyboardButton(text="⏩", callback_data="time_start:right"),
            InlineKeyboardButton(text="⏩⏩", callback_data="time_start:right_fast"),
        ],
        [
            InlineKeyboardButton(text="Конец отрезка", callback_data="ignore"),
        ],
        [
            InlineKeyboardButton(text="⏪⏪", callback_data="time_end:left_fast"),
            InlineKeyboardButton(text="⏪", callback_data="time_end:left"),
            InlineKeyboardButton(text="⏩", callback_data="time_end:right"),
            InlineKeyboardButton(text="⏩⏩", callback_data="time_end:right_fast"),
        ],
        [
            InlineKeyboardButton(text=f"⏱ {start_time:.1f}s - {start_time + duration:.1f}s", callback_data="time_info"),
        ],
        [
            InlineKeyboardButton(text="✅ Готово", callback_data="time_done"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="time_back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def preview_menu() -> InlineKeyboardMarkup:
    """Клавиатура для предпросмотра результата"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Конвертировать", callback_data="preview_convert"),
        ],
        [
            InlineKeyboardButton(text="✂️ Редактировать кроп", callback_data="preview_edit_crop"),
            InlineKeyboardButton(text="⏰ Редактировать время", callback_data="preview_edit_time"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в меню", callback_data="tiktok_back_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
