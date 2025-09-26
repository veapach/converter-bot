# 🎬 TikTok Video Converter Bot

Telegram бот для скачивания и редактирования TikTok видео с возможностью кропа, обрезки по времени и конвертации в WebM.

## 🚀 Быстрый деплой с Docker

### Предварительные требования

1. **Сервер с Docker и Docker Compose**
2. **Telegram Bot Token** (получить у [@BotFather](https://t.me/BotFather))

### Пошаговая инструкция

1. **Подключитесь к серверу и клонируйте репозиторий:**
   ```bash
   git clone https://github.com/yourusername/converter-bot.git
   cd converter-bot
   ```

2. **Создайте файл с переменными окружения:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Добавьте ваш токен бота:
   ```env
   BOT_TOKEN=ваш_токен_от_botfather
   ```

3. **Запустите бота через Docker:**
   ```bash
   # Сделайте скрипт исполняемым
   chmod +x deploy.sh
   
   # Запустите деплой
   ./deploy.sh
   ```

   **Или вручную:**
   ```bash
   docker-compose up -d --build
   ```

4. **Проверьте что бот запустился:**
   ```bash
   docker-compose logs -f
   ```
   
   Вы должны увидеть: `"Bot started successfully"`

## 🛠 Управление ботом

### Полезные команды

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Остановка бота
docker-compose down

# Перезапуск бота
docker-compose restart

# Обновление и перезапуск
git pull
docker-compose down
docker-compose up -d --build

# Просмотр статуса контейнеров
docker-compose ps
```

### Мониторинг

```bash
# Просмотр последних 100 строк логов
docker-compose logs --tail=100

# Просмотр использования ресурсов
docker stats

# Проверка места на диске
df -h
```

## 🔧 Альтернативный деплой (без Docker)

Если хостинг не поддерживает Docker:

### 1. Установка зависимостей

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3-pip python3-venv ffmpeg git
```

**CentOS/RHEL:**
```bash
sudo yum update
sudo yum install python3 python3-pip python3-venv ffmpeg git
# или для новых версий:
sudo dnf install python3 python3-pip python3-venv ffmpeg git
```

### 2. Настройка проекта

```bash
# Клонирование
git clone https://github.com/yourusername/converter-bot.git
cd converter-bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
nano .env
# Добавьте BOT_TOKEN=ваш_токен
```

### 3. Автозапуск через systemd

Создайте сервис:
```bash
sudo nano /etc/systemd/system/tiktok-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=TikTok Converter Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/converter-bot
Environment=PATH=/path/to/converter-bot/venv/bin
ExecStart=/path/to/converter-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Активация сервиса:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tiktok-bot
sudo systemctl start tiktok-bot

# Проверка статуса
sudo systemctl status tiktok-bot

# Просмотр логов
sudo journalctl -u tiktok-bot -f
```

## 🚨 Траблшутинг

### Проблема: Бот не отвечает

1. **Проверьте статус:**
   ```bash
   # Docker
   docker-compose ps
   docker-compose logs converter-bot
   
   # Systemd
   sudo systemctl status tiktok-bot
   sudo journalctl -u tiktok-bot --tail=50
   ```

2. **Проверьте токен бота:**
   ```bash
   cat .env
   # Убедитесь что BOT_TOKEN правильный
   ```

3. **Перезапустите:**
   ```bash
   # Docker
   docker-compose restart
   
   # Systemd
   sudo systemctl restart tiktok-bot
   ```

### Проблема: FFmpeg не найден

**Docker:** Проверьте что в Dockerfile есть установка ffmpeg
**Системный:** Установите ffmpeg:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

### Проблема: Ошибки с временными файлами

1. **Проверьте права доступа:**
   ```bash
   # Docker
   docker-compose exec converter-bot ls -la /tmp/
   
   # Системный
   ls -la /tmp/
   ```

2. **Очистите временные файлы:**
   ```bash
   # Docker
   docker-compose exec converter-bot rm -rf /tmp/tiktok_*
   
   # Системный
   rm -rf /tmp/tiktok_*
   ```

### Проблема: Не хватает места на диске

```bash
# Проверьте место
df -h

# Очистите Docker (осторожно!)
docker system prune -a

# Очистите логи
sudo journalctl --vacuum-time=7d
```

## 📊 Мониторинг и логи

### Docker логи
```bash
# Все логи
docker-compose logs

# Последние N строк
docker-compose logs --tail=100

# В реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs converter-bot
```

### Системные логи
```bash
# Логи сервиса
sudo journalctl -u tiktok-bot -f

# Логи за последний час
sudo journalctl -u tiktok-bot --since "1 hour ago"

# Ошибки
sudo journalctl -u tiktok-bot -p err
```

## 🔧 Настройки и конфигурация

Основные настройки в `app/config.py`:

- **Размеры видео:** ширина, высота, FPS
- **Качество:** CRF параметры (чем меньше - тем лучше качество)
- **Лимиты:** максимальный размер файла (256KB для Telegram)
- **Временные файлы:** автоочистка после обработки

## ✨ Возможности бота

### 📱 TikTok Редактор
- **Автоматическая загрузка** видео с TikTok по ссылке
- **Интерактивная обрезка** с визуальным превью
- **Выбор временного отрезка** до 3 секунд
- **Автосжатие** до лимитов Telegram

### 🎬 Обычная конвертация
- Загрузка любых видеофайлов
- Настройка размера, FPS, качества
- Конвертация в WebM формат

## 🏗 Архитектура

```
converter-bot/
├── app/
│   ├── handlers/          # Обработчики команд и состояний
│   │   ├── start.py       # Команда /start
│   │   ├── video.py       # Обычная конвертация
│   │   ├── tiktok.py      # TikTok редактор
│   │   └── settings.py    # Настройки
│   ├── keyboards/         # Клавиатуры
│   ├── services/          # Бизнес-логика
│   │   ├── converter.py   # Конвертация видео
│   │   └── tiktok.py      # Загрузка TikTok
│   ├── config.py          # Конфигурация
│   └── models.py          # Модели данных
├── main.py               # Точка входа
├── Dockerfile           # Docker образ
├── docker-compose.yml   # Docker Compose конфигурация
├── deploy.sh           # Скрипт автоматического деплоя
└── requirements.txt     # Python зависимости
```

## 🤝 Поддержка

Если возникли проблемы:

1. Проверьте логи
2. Убедитесь что все зависимости установлены
3. Проверьте права доступа к файлам
4. Создайте issue в репозитории

## 📝 Лицензия

MIT License - используйте свободно для личных и коммерческих проектов.