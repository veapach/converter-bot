from dataclasses import dataclass


@dataclass
class Settings:
    width: int
    height: int
    fps: int
    audio: bool
    codec: str
    crf: int
    preset: str

    @staticmethod
    def from_defaults(d) -> "Settings":
        return Settings(
            width=d.width,
            height=d.height,
            fps=d.fps,
            audio=d.audio,
            codec=d.codec,
            crf=d.crf,
            preset=d.preset,
        )
