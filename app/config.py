import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


def _env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name)
    if not val:
        if default is None:
            raise RuntimeError(f"Env var {name} is required")
        return default
    return val


@dataclass(frozen=True)
class Defaults:
    width: int = 512
    height: int = 512
    fps: int = 30
    audio: bool = False
    codec: str = "libvpx-vp9"
    crf: int = 32
    preset: str = "good"


@dataclass(frozen=True)
class Config:
    bot_token: str
    defaults: Defaults

    @staticmethod
    def load() -> "Config":
        load_dotenv()
        token = _env("BOT_TOKEN")
        return Config(bot_token=token, defaults=Defaults())
