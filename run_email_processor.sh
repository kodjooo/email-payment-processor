#!/bin/bash

# Скрипт для запуска email-processor через cron
# Оптимизирован для: нет накопления контейнеров + полные логи + мониторинг

# ВАЖНО: Измените путь на актуальный путь на вашем сервере
PROJECT_DIR="/usr/local/other-scripts/email-processor"
LOG_FILE="$PROJECT_DIR/cron.log"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Функция логирования с выводом в консоль и файл
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Начало выполнения
log "=== Запуск email-processor ==="

# Переход в директорию проекта
cd "$PROJECT_DIR" || {
    log "ОШИБКА: Не удалось перейти в директорию $PROJECT_DIR"
    exit 1
}

# Проверка наличия docker-compose.yml
if [ ! -f "$COMPOSE_FILE" ]; then
    log "ОШИБКА: Файл docker-compose.yml не найден в $PROJECT_DIR"
    exit 1
fi

# Проверка размера лог-файла (архивирование при превышении 10MB)
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt 10485760 ]; then
        log "Архивирование большого лог-файла (размер: $LOG_SIZE байт)"
        mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S)"
        gzip "${LOG_FILE}.$(date +%Y%m%d_%H%M%S)" 2>/dev/null
        log "=== Продолжение после архивирования ==="
    fi
fi

# Загрузка переменных окружения если есть .env файл
if [ -f ".env" ]; then
    log "Загрузка переменных окружения из .env"
    set -a
    source .env
    set +a
else
    log "ПРЕДУПРЕЖДЕНИЕ: Файл .env не найден"
fi

# Проверка доступности Docker
if ! command -v docker >/dev/null 2>&1; then
    log "ОШИБКА: Docker не установлен или недоступен"
    exit 1
fi

# Проверка доступности Docker Compose
if ! docker compose version >/dev/null 2>&1; then
    log "ОШИБКА: Docker Compose не установлен или недоступен"
    exit 1
fi

# Запуск email-processor с автоудалением контейнера
# Используем docker compose run --rm для предотвращения накопления контейнеров
log "Запуск email-processor (режим: run --rm)"

# Захват всех логов: приложения + Docker
docker compose run --rm email-processor 2>&1 | while IFS= read -r line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - APP: $line" >> "$LOG_FILE"
done

# Получение кода выхода из PIPESTATUS
EXIT_CODE=${PIPESTATUS[0]}

# Проверка результата выполнения
if [ $EXIT_CODE -eq 0 ]; then
    log "✅ Email-processor завершился успешно (код выхода: $EXIT_CODE)"
else
    log "❌ ОШИБКА: Email-processor завершился с ошибкой (код выхода: $EXIT_CODE)"
fi

# Дополнительная очистка: удаление осиротевших контейнеров и образов
log "Выполнение очистки Docker..."
PRUNE_OUTPUT=$(docker container prune -f 2>&1)
if [ -n "$PRUNE_OUTPUT" ] && [ "$PRUNE_OUTPUT" != "Total reclaimed space: 0B" ]; then
    log "Очистка контейнеров: $PRUNE_OUTPUT"
fi

# Очистка старых логов cron (сохраняем последние 30 дней)
CLEANED_LOGS=$(find "$PROJECT_DIR" -name "cron.log*" -type f -mtime +30 2>/dev/null)
if [ -n "$CLEANED_LOGS" ]; then
    echo "$CLEANED_LOGS" | while read -r old_log; do
        rm -f "$old_log"
        log "Удален старый лог: $(basename "$old_log")"
    done
fi

# Статистика выполнения
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
log "=== Завершение работы ($END_TIME) ==="

# Возврат кода выхода для мониторинга в cron
exit $EXIT_CODE
