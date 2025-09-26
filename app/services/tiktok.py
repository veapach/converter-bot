import os
import tempfile
import cv2
import asyncio
import yt_dlp
import logging
from PIL import Image, ImageDraw
from typing import Tuple, Optional
from pathlib import Path

# Настраиваем логирование для yt-dlp
logging.getLogger('yt_dlp').setLevel(logging.WARNING)


class TikTokDownloader:
    def __init__(self):
        self.temp_dir = None
        
    async def download_video(self, url: str) -> str:
        """Загружает видео с TikTok и возвращает путь к файлу"""
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")
        
        # Список форматов для попытки загрузки (от лучшего к худшему)
        format_options = [
            'best[height<=720][ext=mp4]',  # Лучшее качество MP4 до 720p
            'best[ext=mp4]',               # Лучшее MP4 качество
            'best[height<=720]',           # Лучшее качество до 720p любого формата
            'best',                        # Лучшее доступное качество
            'worst'                        # В крайнем случае - худшее качество
        ]
        
        def download():
            last_error = None
            for fmt in format_options:
                try:
                    ydl_opts = {
                        'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
                        'format': fmt,
                        'no_warnings': True,
                        'ignoreerrors': False,
                        'cookiefile': None,
                        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'referer': 'https://www.tiktok.com/',
                        'extractor_retries': 3,
                        'fragment_retries': 3,
                        'skip_unavailable_fragments': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    return  # Успешная загрузка
                except Exception as e:
                    last_error = e
                    continue
                    
            # Если все форматы не сработали, выбрасываем последнюю ошибку
            if last_error:
                raise last_error
        
        # Запускаем загрузку в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download)
        
        # Найдем загруженный файл
        files = list(Path(self.temp_dir).glob("*"))
        if not files:
            raise ValueError("Не удалось загрузить видео")
        
        return str(files[0])
    
    def cleanup(self):
        """Очистка временных файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class VideoEditor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.frame_count / self.fps if self.fps > 0 else 0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def get_frame_at_time(self, time_seconds: float) -> Optional[bytes]:
        """Получает кадр в заданное время в виде JPEG байтов"""
        frame_number = int(time_seconds * self.fps)
        if frame_number >= self.frame_count:
            frame_number = self.frame_count - 1
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        # Конвертируем в RGB для PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Конвертируем в PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Сохраняем в байты
        import io
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    def create_crop_preview(self, crop_x: int, crop_y: int, crop_width: int, crop_height: int, time_seconds: float = 0) -> Optional[bytes]:
        """Создает превью с красным квадратом обрезки"""
        frame_bytes = self.get_frame_at_time(time_seconds)
        if not frame_bytes:
            return None
        
        # Загружаем изображение
        from io import BytesIO
        image = Image.open(BytesIO(frame_bytes))
        
        # Создаем копию для рисования
        draw_image = image.copy()
        draw = ImageDraw.Draw(draw_image)
        
        # Рисуем красный прямоугольник
        draw.rectangle(
            [crop_x, crop_y, crop_x + crop_width, crop_y + crop_height],
            outline='red',
            width=3
        )
        
        # Затемняем области вне кропа
        # Создаем маску
        mask = Image.new('RGBA', image.size, (0, 0, 0, 128))
        mask_draw = ImageDraw.Draw(mask)
        
        # Рисуем прозрачную область в месте кропа
        mask_draw.rectangle(
            [crop_x, crop_y, crop_x + crop_width, crop_y + crop_height],
            fill=(0, 0, 0, 0)
        )
        
        # Применяем маску
        if draw_image.mode != 'RGBA':
            draw_image = draw_image.convert('RGBA')
        
        draw_image = Image.alpha_composite(draw_image, mask)
        draw_image = draw_image.convert('RGB')
        
        # Снова рисуем красную рамку поверх всего
        draw = ImageDraw.Draw(draw_image)
        draw.rectangle(
            [crop_x, crop_y, crop_x + crop_width, crop_y + crop_height],
            outline='red',
            width=3
        )
        
        # Сохраняем в байты
        buffer = BytesIO()
        draw_image.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    def calculate_crop_bounds(self, crop_width: int, crop_height: int) -> Tuple[int, int, int, int]:
        """Вычисляет границы кропа по центру видео"""
        center_x = self.width // 2
        center_y = self.height // 2
        
        crop_x = max(0, center_x - crop_width // 2)
        crop_y = max(0, center_y - crop_height // 2)
        
        # Убеждаемся, что кроп не выходит за границы
        if crop_x + crop_width > self.width:
            crop_x = self.width - crop_width
        if crop_y + crop_height > self.height:
            crop_y = self.height - crop_height
        
        return crop_x, crop_y, crop_width, crop_height
    
    def create_time_preview(self, start_time: float, duration: float, crop_params: Tuple[int, int, int, int]) -> Optional[bytes]:
        """Создает превью временного отрезка"""
        try:
            # Берем кадр из середины выбранного отрезка
            middle_time = start_time + duration / 2
            
            # Убеждаемся, что время в пределах видео
            if middle_time >= self.duration:
                middle_time = self.duration - 0.1
            if middle_time < 0:
                middle_time = 0
            
            crop_x, crop_y, crop_width, crop_height = crop_params
            
            print(f"DEBUG: Creating time preview for time {middle_time:.2f}s, crop: {crop_x},{crop_y},{crop_width}x{crop_height}")
            
            result = self.create_crop_preview(crop_x, crop_y, crop_width, crop_height, middle_time)
            
            if result:
                print(f"DEBUG: Time preview created successfully, size: {len(result)} bytes")
            else:
                print("DEBUG: Time preview creation failed - no result")
                
            return result
        except Exception as e:
            print(f"DEBUG: Error creating time preview: {e}")
            return None
    
    def get_video_info(self) -> dict:
        """Возвращает информацию о видео"""
        return {
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'duration': self.duration,
            'frame_count': self.frame_count
        }
    
    async def create_video_preview(self, start_time: float, duration: float, crop_params: Tuple[int, int, int, int], output_path: str) -> bool:
        """Создает короткое превью видео"""
        try:
            crop_x, crop_y, crop_width, crop_height = crop_params
            
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(start_time),
                "-t", str(min(duration, 2.0)),  # Максимум 2 секунды для превью
                "-i", self.video_path,
                "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}",
                "-r", "15",  # Низкий FPS для превью
                "-crf", "35",  # Низкое качество для превью
                "-an",  # Без аудио
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return process.returncode == 0 and os.path.exists(output_path)
        except Exception as e:
            print(f"DEBUG: Error creating video preview: {e}")
            return False
    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()