# Быстрый старт

## 1. Настройка конфигурации

Создайте файл `.env` в корне проекта email-processor:

```bash
cp env.example .env
```

Заполните основные параметры:

```env
# Обязательные настройки Email
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Обязательные настройки Webhook  
WEBHOOK_URL=https://your-server.com/webhook/payments
WEBHOOK_TOKEN=your_secret_token

# Настройки CSV (адаптируйте под ваши данные)
CSV_FILTER_COLUMN=status
CSV_FILTER_VALUE=completed
PAYMENT_AMOUNT_COLUMN=amount
PAYMENT_DATE_COLUMN=date
PAYMENT_ID_COLUMN=transaction_id
CUSTOMER_ID_COLUMN=customer_id
```

## 2. Запуск с Docker (рекомендуется)

```bash
# Из корневой директории проекта
docker-compose up -d

# Просмотр логов
docker-compose logs -f email-processor
```

## 3. Локальный запуск

```bash
cd email-processor

# Установка зависимостей
pip install -r requirements.txt

# Одноразовый запуск
python src/main.py --mode once

# Непрерывный мониторинг (каждые 30 минут)  
python src/main.py --mode continuous --interval 30
```

## 4. Проверка работы

Система будет:
- ✅ Подключаться к вашей почте
- ✅ Искать письма с ссылками для скачивания
- ✅ Скачивать и распаковывать архивы
- ✅ Обрабатывать CSV файлы
- ✅ Отправлять данные на ваш webhook

## 5. Мониторинг

Логи сохраняются в папке `logs/` или смотрите через Docker:

```bash
docker-compose logs email-processor
```

## Типичные проблемы

- **Не подключается к Gmail**: Используйте App Password вместо обычного пароля
- **Браузер не запускается**: Убедитесь что установлен Google Chrome
- **CSV не обрабатывается**: Проверьте названия колонок в настройках

## Webhook тестирование

Можно использовать https://webhook.site для тестирования webhook'ов.
