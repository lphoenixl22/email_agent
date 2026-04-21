#!/bin/bash

# Скрипт быстрой установки и настройки lab_checker

set -e

echo "========================================="
echo "Установка Lab Checker Service"
echo "========================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не найден"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Найден Python $PYTHON_VERSION"

# Создание виртуального окружения
echo ""
echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo ""
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Копирование файла конфигурации
if [ ! -f .env ]; then
    echo ""
    echo "Создание файла .env из .env.example..."
    cp .env.example .env
    echo "Не забудьте отредактировать .env и указать ваши данные!"
fi

# Проверка Ollama
echo ""
echo "Проверка Ollama..."
if command -v ollama &> /dev/null; then
    echo "Ollama найден"
    ollama list
else
    echo "WARNING: Ollama не найден!"
    echo "Установите Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "Затем загрузите модель: ollama pull llama3.2"
fi

# Создание директорий
mkdir -p config/labs
mkdir -p logs
mkdir -p /tmp/lab_checker

echo ""
echo "========================================="
echo "Установка завершена!"
echo "========================================="
echo ""
echo "Следующие шаги:"
echo "1. Отредактируйте файл .env и укажите:"
echo "   - IMAP учетные данные вашей почты"
echo "   - Настройки Ollama (если используете)"
echo "   - Google Sheets credentials (если используете)"
echo ""
echo "2. Загрузите модель Ollama:"
echo "   ollama pull llama3.2"
echo ""
echo "3. Для запуска сервиса:"
echo "   source venv/bin/activate"
echo "   python src/main.py"
echo ""
echo "4. Для однократной проверки:"
echo "   python src/main.py --once"
echo ""
