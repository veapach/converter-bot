#!/bin/bash

# Скрипт для деплоя TikTok Converter Bot

echo "🚀 Деплой TikTok Converter Bot"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env на основе .env.example:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    echo "   # Добавьте ваш BOT_TOKEN"
    exit 1
fi

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "📦 Установите Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "📦 Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Останавливаем и удаляем старые контейнеры
echo "🛑 Останавливаем старые контейнеры..."
docker-compose down

# Пересобираем образ
echo "🔨 Пересобираем образ..."
docker-compose build --no-cache

# Запускаем
echo "▶️  Запускаем бота..."
docker-compose up -d

# Показываем логи
echo "📋 Логи бота:"
docker-compose logs -f

echo "✅ Бот запущен!"
echo "📊 Для просмотра логов: docker-compose logs -f"
echo "🛑 Для остановки: docker-compose down"