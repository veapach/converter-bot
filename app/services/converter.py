import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from app.models import Settings


class FFmpegError(Exception):
    pass


class Converter:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg = ffmpeg_path or os.getenv("FFMPEG_PATH") or "ffmpeg"
        self._proc: Optional[asyncio.subprocess.Process] = None

    async def convert(self, input_path: str, settings: Settings) -> str:
        out_dir = tempfile.mkdtemp(prefix="conv_")
        out_path = str(Path(out_dir) / "output.webm")
        exec_path: Optional[str]
        if os.path.isabs(self.ffmpeg) or os.path.sep in self.ffmpeg:
            exec_path = self.ffmpeg if os.path.exists(self.ffmpeg) else None
        else:
            exec_path = shutil.which(self.ffmpeg)
        if not exec_path:
            raise FFmpegError("ffmpeg не найден. Установите ffmpeg и добавьте его в PATH или задайте FFMPEG_PATH.")

        args = [
            exec_path,
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={settings.width}:{settings.height}:flags=lanczos",
            "-r",
            str(settings.fps),
            "-an" if not settings.audio else "-c:a",
        ]
        if settings.audio:
            args += ["libopus", "-b:a", "96k"]
        v_args = [
            "-c:v",
            settings.codec,
            "-crf",
            str(settings.crf),
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-deadline",
            settings.preset,
        ]
        cmd = args + v_args + [out_path]
        self._proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await self._proc.communicate()
        except asyncio.CancelledError:
            try:
                if self._proc and self._proc.returncode is None:
                    self._proc.terminate()
                    try:
                        await asyncio.wait_for(self._proc.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        self._proc.kill()
            finally:
                self._proc = None
            raise FFmpegError("Конвертация отменена")
        finally:
            self._proc = None
        if (self._proc and self._proc.returncode != 0) or not os.path.exists(out_path):
            err_text = (stderr or b"").decode("utf-8", errors="ignore")
            raise FFmpegError(err_text)
        return out_path

    def cancel(self):
        proc = self._proc
        if proc and proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
