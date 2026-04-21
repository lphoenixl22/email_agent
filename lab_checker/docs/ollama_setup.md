# Инструкция по установке и настройке Ollama

## Шаг 1: Установка Ollama

### Linux/macOS

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows

1. Скачайте установщик с [официального сайта](https://ollama.ai/download)
2. Запустите установщик
3. Следуйте инструкциям мастера установки

## Шаг 2: Проверка установки

```bash
ollama --version
```

## Шаг 3: Загрузка модели

Рекомендуемые модели для анализа текста на русском языке:

```bash
# Llama 3.2 (легкая и быстрая)
ollama pull llama3.2

# Llama 3.1 8B (хорошее качество)
ollama pull llama3.1

# Mistral (хорошая поддержка русского)
ollama pull mistral

# Saiga (специализированная русскоязычная модель)
ollama pull saiga
```

## Шаг 4: Проверка работы модели

```bash
ollama run llama3.2 "Привет! Как дела?"
```

## Шаг 5: Настройка сервиса

В файле `.env` укажите используемую модель:

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Шаг 6: Запуск Ollama как службы (опционально)

### Linux (systemd)

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

### macOS (launchd)

Ollama запускается автоматически при установке.

### Windows

Ollama работает как фоновое приложение.

## Рекомендуемые модели

| Модель | Размер | Качество | Скорость | Русский язык |
|--------|--------|----------|----------|--------------|
| llama3.2 | 3GB | Хорошее | Быстро | Средне |
| llama3.1:8b | 5GB | Очень хорошее | Средне | Хорошо |
| mistral | 4GB | Хорошее | Быстро | Хорошо |
| saiga | 4GB | Отличное | Средне | Отлично |

## Troubleshooting

### Ошибка "connection refused"

Убедитесь, что Ollama запущен:

```bash
ollama serve
```

### Модель загружается медленно

Первый запуск модели требует загрузки весов в память. Последующие запуски будут быстрее.

### Недостаточно памяти

Используйте более легкую модель:

```bash
ollama pull phi3  # Модель всего 2GB
```

### Обновление моделей

```bash
ollama pull --force llama3.2
```

## API Ollama

Сервис использует HTTP API Ollama:

- Адрес: `http://localhost:11434`
- Endpoint: `/api/chat`

Проверка доступности API:

```bash
curl http://localhost:11434/api/tags
```
