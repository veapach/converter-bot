#!/bin/bash

# Скрипт для установки бота как системного сервиса

if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo ./install-service.sh"
    exit 1
fi

echo "🔧 Установка TikTok Bot как системного сервиса"

# Получаем текущего пользователя и путь
CURRENT_USER=${SUDO_USER:-$USER}
CURRENT_DIR=$(pwd)
VENV_PATH="$CURRENT_DIR/venv/bin"

echo "👤 Пользователь: $CURRENT_USER"
echo "📁 Рабочая директория: $CURRENT_DIR"

# Создаем файл сервиса
cat > /etc/systemd/system/tiktok-bot.service << EOF
[Unit]
Description=TikTok Converter Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$VENV_PATH
ExecStart=$VENV_PATH/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "📝 Создан файл сервиса: /etc/systemd/system/tiktok-bot.service"

# Перезагружаем systemd
systemctl daemon-reload

# Включаем автозапуск
systemctl enable tiktok-bot

echo "✅ Сервис установлен!"
echo ""
echo "🚀 Управление сервисом:"
echo "   sudo systemctl start tiktok-bot     # Запуск"
echo "   sudo systemctl stop tiktok-bot      # Остановка"
echo "   sudo systemctl restart tiktok-bot   # Перезапуск"
echo "   sudo systemctl status tiktok-bot    # Статус"
echo ""
echo "📋 Просмотр логов:"
echo "   sudo journalctl -u tiktok-bot -f    # В реальном времени"
echo "   sudo journalctl -u tiktok-bot --tail=100  # Последние 100 строк"
echo ""
echo "▶️  Запустить сейчас? (y/n)"
read -r response
if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    systemctl start tiktok-bot
    echo "🎉 Бот запущен!"
    echo "📊 Статус:"
    systemctl status tiktok-bot
fi