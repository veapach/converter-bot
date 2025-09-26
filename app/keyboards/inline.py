from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎬 Конвертировать видео", callback_data="convert")],
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
