#!/bin/bash

# Простой скрипт установки без Docker

echo "🎬 Установка TikTok Converter Bot"

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден!"
    echo "📦 Установите Python3:"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

# Проверяем FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg не найден!"
    echo "📦 Установите FFmpeg:"
    echo "Ubuntu/Debian: sudo apt install ffmpeg"
    echo "CentOS/RHEL: sudo yum install ffmpeg"
    exit 1
fi

# Проверяем .env файл
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    echo "   # Добавьте: BOT_TOKEN=ваш_токен"
    exit 1
fi

# Создаем виртуальное окружение
echo "🔧 Создаем виртуальное окружение..."
python3 -m venv venv

# Активируем окружение
echo "📦 Активируем окружение..."
source venv/bin/activate

# Устанавливаем зависимости
echo "⬇️  Устанавливаем зависимости..."
pip install -r requirements.txt

echo "✅ Установка завершена!"
echo ""
echo "🚀 Для запуска используйте:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "🔧 Для создания системного сервиса:"
echo "   sudo ./install-service.sh"