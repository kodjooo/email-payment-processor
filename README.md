# 📧 Email Payment Processor

Автоматизированная система для обработки платежных данных из электронной почты с использованием Python и Docker.

## 🎯 Описание

Система автоматически:
- 📧 Получает новые письма с почтового сервера через IMAP
- 🔍 Ищет в письмах ссылки для скачивания файлов
- 🤖 Использует автоматизацию браузера для клика на кнопки и скачивания архивов
- 📦 Распаковывает архивы (ZIP, RAR, 7Z)
- 📊 Обрабатывает CSV файлы с платежными данными
- 💰 Извлекает информацию об оплатах согласно заданным условиям
- 🔗 Отправляет webhook с данными об оплатах на внешний сервер
- 🕒 Работает по встроенному расписанию: ежедневно в 11:00 по МСК без использования cron

## ⚡ Быстрый старт

### 🚀 Готовый к использованию (только Docker)

```bash
# 1. Создайте .env файл с настройками email и webhook
# 2. Соберите образ:
docker-compose build email-processor
# 3. Запустите контейнер (рекомендуемый способ — в фоне):
docker-compose up -d email-processor
```

Контейнер должен оставаться запущенным: встроенный планировщик выполнит обработку автоматически каждый день в 11:00 по МСК.

⚠️ **Возможные проблемы при запуске:**
- **Конфликт имен контейнеров:** `docker rm email-processor` перед запуском
- **Ошибка браузера:** перезапустите Docker Desktop или подождите 15 минут

### Docker (подробная инструкция)

```bash
# Клонируйте репозиторий
git clone https://github.com/kodjooo/email-payment-processor.git
cd email-processor

# Настройте конфигурацию
# Создайте .env файл в корне проекта (рядом с docker-compose.yml)
nano .env

# Запустите систему (рекомендуемый способ)
docker-compose up email-processor

# Альтернативно через docker run
docker run --rm --name email-processor --env-file .env emailprocessor-email-processor:latest

# Для повторного запуска (если нет конфликта имен)
docker-compose up email-processor

# Если возникает конфликт имен контейнеров:
docker rm email-processor
docker-compose up email-processor

# Полезные Docker команды:
docker ps -a                             # Статус всех контейнеров
docker ps -a | grep email-processor      # Только email-processor контейнеры
docker rm email-processor                # Удаление остановленного контейнера
docker logs email-processor              # Просмотр логов (если контейнер запущен)
docker images | grep cursor              # Список образов
docker-compose build email-processor     # Пересборка образа
```

### Локальная установка

```bash
cd email-processor
pip install -r requirements.txt
python src/main.py --mode once
```

## 📋 Конфигурация

Создайте файл `.env` в корне проекта (рядом с `docker-compose.yml`) с настройками:

```env
# Email Configuration (обязательно)
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
MAILBOX=INBOX
USE_SSL=true

# Webhook Configuration (обязательно)
WEBHOOK_URL=https://your-server.com/webhook/payments
WEBHOOK_TOKEN=your_secret_token
WEBHOOK_TIMEOUT=30

# CSV Processing Configuration
CSV_FILTER_COLUMN="Наименование контрагента"
CSV_FILTER_VALUE="АО \"ТБанк\""
PAYMENT_AMOUNT_COLUMN="Сумма в валюте счёта"
PAYMENT_DATE_COLUMN="Дата проведения"
PAYMENT_ID_COLUMN="Назначение платежа"
CUSTOMER_ID_COLUMN="ИНН контрагента"

# Browser Configuration
BROWSER_HEADLESS=true
DOWNLOAD_TIMEOUT=60
IMPLICIT_WAIT=10

# Logging
LOG_LEVEL=INFO

# Schedule Configuration
SCHEDULE_TIMEZONE=Europe/Moscow
SCHEDULE_HOUR=11
SCHEDULE_MINUTE=0
```

## 🏗️ Архитектура

```
📧 Email Server → 📨 Email Handler → 🔍 Link Extraction → 
🤖 Browser Automation → 📦 File Download → 🗃️ Archive Extraction → 
📊 CSV Processing → 💰 Payment Extraction → 📡 Webhook Sender → 🖥️ External Server
```

## 📁 Структура проекта

```
email-processor-root/
├── README.md                    # Документация
├── docker-compose.yml           # Docker композиция
├── .gitignore                   # Git исключения
└── email-processor/             # Основное приложение
    ├── src/                     # Исходный код
    │   ├── main.py              # Главный скрипт
    │   ├── email_handler.py     # Работа с email
    │   ├── email_tracking.py    # Отслеживание обработанных писем
    │   ├── browser_automation.py # Автоматизация браузера
    │   ├── file_processor.py    # Обработка файлов
    │   └── webhook_sender.py    # Отправка webhook
    ├── config/                  # Конфигурация
    │   └── config.py            # Настройки приложения
    ├── downloads/               # Скачанные файлы (Docker volume)
    ├── logs/                    # Логи приложения (Docker volume)
    ├── requirements.txt         # Python зависимости
    ├── Dockerfile              # Docker образ
├── .env                         # Конфигурация (создать в корне)
```

## 🔧 Возможности

- ✅ **Модульная архитектура** - легко расширяемая и настраиваемая
- ✅ **Docker поддержка** - готов к развертыванию в контейнерах
- ✅ **Автоматизация браузера** - обработка сложных веб-форм
- ✅ **Множество форматов архивов** - ZIP, RAR, 7Z
- ✅ **Гибкая обработка CSV** - настраиваемые поля и условия
- ✅ **Webhook интеграция** - отправка данных в реальном времени
- ✅ **Детальное логирование** - полный мониторинг процесса
- ✅ **Безопасность** - переменные окружения для чувствительных данных

## 📊 Формат Webhook

```json
{
  "timestamp": "2025-08-31T14:58:37.189815",
  "data": {
    "payments_count": 2,
    "payments": [
      {
        "transaction_id": "2491",
        "customer_id": 772746611830,
        "amount": 2500,
        "currency": "RUB",
        "date": "2025-08-28T00:00:00",
        "purpose": "НДС не облагается. Счёт 2491",
        "source_file": "Выписка_ООО \"АДВАНТО\"_40702810810001014566_28.08.2025-28.08.2025.csv"
      },
      {
        "transaction_id": "2497", 
        "customer_id": 7751019223,
        "amount": 2500,
        "currency": "RUB",
        "date": "2025-08-28T00:00:00",
        "purpose": "Оплата по счету №2497 от 28.08.2025 г., за услуги. Сумма 2500-00 руб. Без НДС",
        "source_file": "Выписка_ООО \"АДВАНТО\"_40702810810001014566_28.08.2025-28.08.2025.csv"
      }
    ]
  }
}
```

## 🛠️ Требования

- Python 3.11+
- Google Chrome (для автоматизации)
- IMAP доступ к email
- Docker (для контейнеризации)

## 🔧 Управление Docker

### Основные команды

```bash
# Запуск (контейнер завершится после обработки)
docker-compose up email-processor

# Запуск и просмотр логов
docker-compose up email-processor

# Просмотр логов после завершения
docker-compose logs email-processor
docker-compose logs --tail=100 email-processor  # Последние 100 строк

# Повторный запуск
docker-compose up --force-recreate email-processor

# Полная пересборка (после изменений в коде)
docker-compose down
docker-compose up --build email-processor

# Очистка volumes (удалит логи и скачанные файлы)
docker-compose down -v
```

### Мониторинг и отладка

```bash
# Вход в контейнер для отладки
docker-compose exec email-processor bash

# Просмотр использования ресурсов
docker stats email-processor

# Просмотр volumes
docker volume ls | grep email-processor

# Путь к логам на хост-системе
docker volume inspect emailprocessor_email_processor_logs
```

### Режимы работы

Контейнер запускается и **завершает работу после обработки** всех найденных писем без автоматического перезапуска.

```bash
# Разовая обработка (рекомендуемый способ)
docker-compose up email-processor

# Повторная обработка
docker-compose up email-processor

# Если возникает конфликт имен:
docker rm email-processor
docker-compose up email-processor

# Пересборка образа (после изменений кода)
docker-compose build email-processor

# Запуск после пересборки
docker-compose up email-processor

# Альтернативный запуск через docker run:
docker run --rm --name email-processor --env-file .env emailprocessor-email-processor:latest
```

**Особенности:**
- Режим `restart: "no"` - контейнер не перезапускается автоматически
- После завершения обработки контейнер останавливается с кодом 0
- Для повторного запуска используйте команды выше
- Временные файлы автоматически очищаются после обработки

## 🕒 Автоматический запуск по расписанию

Внутри контейнера работает собственный планировщик на `pytz`. Достаточно запустить сервис командой:

```bash
docker-compose up -d email-processor
```

Контейнер остаётся активным и выполняет обработку автоматически каждый день в 11:00 по МСК. Для разового запуска вручную используйте:

```bash
docker compose run --rm email-processor
```

## 📊 Логирование

### Настройки логов
- **Приложение**: Ротация каждые 10 MB, хранение 30 дней
- **Контейнер**: Логи доступны через `docker compose logs email-processor`
- **Формат**: timestamp | level | module:function:line | message

### Файлы логов
```
email-processor/
└── logs/
    └── email_processor.log      # Логи приложения (Docker volume)
```

### Мониторинг логов
```bash
# Потоковые логи контейнера (как stdout cron раньше)
docker compose logs -f email-processor

# Логи приложения из volume
docker compose exec email-processor tail -f /app/logs/email_processor.log

# Поиск ошибок за последний день
docker compose logs email-processor | grep -i error

# Статистика успешных/неуспешных запусков
docker compose logs email-processor | grep -E "(Cycle completed|завершился)"
```

## 📖 Документация

Вся необходимая информация для работы с проектом содержится в этом файле.

## 🚨 Решение частых проблем

### Ошибка "Conflict. The container name is already in use"

```bash
# Проблема: Пытаетесь запустить контейнер с именем, которое уже используется
# Решение:
docker rm email-processor              # Удалить старый контейнер
docker-compose up email-processor      # Запустить заново

# Или проверить статус контейнеров:
docker ps -a | grep email-processor    # Посмотреть все контейнеры
```

### Ошибка браузера или зависание

```bash
# Проблема: Браузер не может запуститься или зависает
# Решения:
docker restart $(docker ps -q)         # Перезапуск всех контейнеров
# или
docker system prune -f                 # Очистка Docker кеша
docker-compose up --force-recreate email-processor
```

### Проблемы с .env файлом

```bash
# Проверьте, что .env файл существует и доступен:
ls -la .env                           # Должен показать файл
cat .env | head -5                    # Проверьте содержимое (первые 5 строк)

# Убедитесь, что .env находится в корне проекта (рядом с docker-compose.yml)
```

### Контейнер сразу завершается

```bash
# Просмотрите логи для диагностики:
docker-compose logs email-processor   # Показать все логи
docker-compose logs --tail=50 email-processor  # Последние 50 строк

# Частые причины:
# - Неверные данные в .env (email, пароль)
# - Отсутствует интернет соединение
# - Проблемы с правами доступа
```

## ❗ Важные особенности

### Email конфигурация
- **EMAIL_ADDRESS**: Ваш Gmail адрес
- **EMAIL_PASSWORD**: App Password (не обычный пароль!)
- Система ищет письма с темой: `Выписка по счету ООО "АДВАНТО"`
- Обрабатывает только письма с download ссылками

### CSV обработка  
- Настройки предназначены для российских банковских выписок
- Фильтрует платежи по контрагенту (по умолчанию: АО "ТБанк")
- Извлекает: ИНН, сумму, дату, назначение платежа

### Browser automation
- Использует Chromium в headless режиме
- Автоматически скачивает ZIP/RAR/7Z архивы
- Требует X11 (предустановлен в Docker)

## 🔒 Безопасность

- 🔐 Используйте App Passwords для Gmail ([инструкция](https://support.google.com/accounts/answer/185833))
- 🛡️ Храните чувствительные данные только в .env файле
- 🔒 Используйте HTTPS для webhook URL
- 📝 Регулярно проверяйте логи на наличие ошибок
- 🚫 Никогда не коммитьте .env файл в git

## 🤝 Поддержка

Для вопросов и поддержки создайте issue в репозитории.

## 📄 Лицензия

MIT License
