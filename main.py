import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import Config
from app.handlers.start import router as start_router
from app.handlers.settings import router as settings_router
from app.handlers.video import router as video_router


async def main() -> None:
	logging.basicConfig(level=logging.INFO)
	cfg = Config.load()
	bot = Bot(token=cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
	dp = Dispatcher(storage=MemoryStorage())
	dp.include_router(start_router)
	dp.include_router(settings_router)
	dp.include_router(video_router)
	await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
	asyncio.run(main())

