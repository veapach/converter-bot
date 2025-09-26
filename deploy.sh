#!/bin/bash

# Скрипт для деплоя TikTok Converter Bot

echo "🚀 Деплой TikTok Converter Bot"
echo "================================"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env на основе .env.example:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    echo "   # Добавьте ваш BOT_TOKEN"
    exit 1
fi

# Проверяем токен в .env
if ! grep -q "BOT_TOKEN=" .env || grep -q "BOT_TOKEN=your_bot_token_here" .env; then
    echo "❌ BOT_TOKEN не настроен в .env файле!"
    echo "📝 Отредактируйте .env файл и добавьте настоящий токен"
    exit 1
fi

echo "✅ Файл .env найден и настроен"

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "📦 Установите Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

echo "✅ Docker найден: $(docker --version)"

# Проверяем наличие Docker Compose (новая или старая версия)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "📦 Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Определяем какую команду использовать для Docker Compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo "✅ Docker Compose найден: $(docker-compose --version)"
else
    DOCKER_COMPOSE="docker compose"
    echo "✅ Docker Compose найден: $(docker compose version)"
fi

echo ""
echo "🔧 Используем команду: $DOCKER_COMPOSE"
echo ""

# Останавливаем и удаляем старые контейнеры
echo "🛑 Останавливаем старые контейнеры..."
$DOCKER_COMPOSE down 2>/dev/null || echo "   (контейнеры не запущены)"

# Пересобираем образ
echo "🔨 Пересобираем образ..."
$DOCKER_COMPOSE build --no-cache

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при сборке образа!"
    exit 1
fi

# Запускаем
echo "▶️  Запускаем бота..."
$DOCKER_COMPOSE up -d

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при запуске контейнера!"
    exit 1
fi

echo ""
echo "✅ Бот успешно запущен!"
echo ""
echo "� Полезные команды:"
echo "   $DOCKER_COMPOSE logs -f              # Просмотр логов в реальном времени"
echo "   $DOCKER_COMPOSE logs --tail=100      # Последние 100 строк логов"
echo "   $DOCKER_COMPOSE ps                   # Статус контейнеров"
echo "   $DOCKER_COMPOSE restart              # Перезапуск"
echo "   $DOCKER_COMPOSE down                 # Остановка"
echo ""
echo "📋 Проверяем статус..."
$DOCKER_COMPOSE ps

echo ""
echo "🎯 Показываем последние логи (нажмите Ctrl+C для выхода):"
echo "================================"
sleep 2
$DOCKER_COMPOSE logs -f