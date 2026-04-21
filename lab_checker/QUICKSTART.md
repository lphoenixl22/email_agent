# Быстрый старт - Lab Checker для MikroTik

## 1. Установка за 5 минут

```bash
# Клонирование и переход в директорию
cd lab_checker

# Установка зависимостей Python
pip install -r requirements.txt

# Установка Tesseract OCR (для скриншотов)
sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

## 2. Настройка Ollama (локальная LLM)

```bash
# Установка Ollama (если нет)
curl -fsSL https://ollama.com/install.sh | sh

# Скачивание модели
ollama pull llama3.2

# Проверка работы
ollama run llama3.2 "Привет, как дела?"
```

## 3. Конфигурация

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
nano .env
```

**Минимальная конфигурация:**
```ini
# Почта (IMAP)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your.email@gmail.com
IMAP_PASSWORD=app_password_here

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## 4. Запуск

```bash
# Однократная проверка почты
python src/main.py --once

# Постоянная работа (проверка каждые 60 сек)
python src/main.py
```

## 5. Как это работает

### Студент отправляет:
📧 Письмо с темой "Лабораторная №1"  
📎 Вложения: 
- `export.txt` - вывод команд MikroTik
- `topology.png` - скриншот топологии
- `ping_result.jpg` - скриншот ping тестов

### Система делает:
1. ✅ Получает письмо через IMAP
2. 📄 Извлекает текст из TXT/PNG/JPG (OCR)
3. 🔍 Проверяет на плагиат (сравнение с другими работами)
4. 🤖 Анализирует через локальную LLM
5. 📊 Выставляет балл в Google Таблицу

## Пример отчета студента

**Файл: `lab1_ivanov.txt`**
```
Лабораторная работа №1
Студент: Иванов Иван, группа ПИ-202

/system identity set name=left

interface print
# Flags: D - dynamic, X - disabled, R - running
#  0  R  ether1
#  1  R  ether2

ip address add address=192.168.0.1/24 interface=ether1
ip address add address=192.168.1.1/24 interface=ether2

ip address print
# 0   192.168.0.1/24     192.168.0.0     ether1
# 1   192.168.1.1/24     192.168.1.0     ether2

Вывод: Настроил IP адреса на двух интерфейсах.
```

## Поддерживаемые форматы

| Формат | Описание | Требуется |
|--------|----------|-----------|
| `.txt` | Export конфигурации MikroTik | ✅ |
| `.png` | Скриншоты топологии, ping | OCR |
| `.jpg` | Скриншоты WinBox | OCR |
| `.pdf` | Документы с отчетом | PyPDF2 |
| `.docx` | Word документы | python-docx |

## Проверка установки

```bash
# Проверка Python зависимостей
python -c "import ollama, pytesseract, PyPDF2; print('OK')"

# Проверка Tesseract
tesseract --version
tesseract --list-langs  # должны быть eng, rus

# Проверка Ollama
ollama list  # должна быть llama3.2
```

## Troubleshooting

**Ошибка: "Модель недоступна"**
```bash
ollama pull llama3.2
ollama serve
```

**Ошибка: "OCR не работает"**
```bash
# Проверьте установку tesseract
which tesseract
tesseract --list-langs

# Если нет русских языков
sudo apt install tesseract-ocr-rus
```

**Письма не читаются**
- Для Gmail используйте App Password: https://myaccount.google.com/apppasswords
- Включите IMAP в настройках почты

## Документация

- 📖 [Руководство по MikroTik](docs/mikrotik_guide.md) - критерии оценки
- 🔧 [Настройка Ollama](docs/ollama_setup.md) - детали установки LLM
- 📊 [Google Sheets](docs/google_sheets_setup.md) - интеграция с таблицами

## Пример использования

```python
from src.main import LabCheckerService

# Создание сервиса
service = LabCheckerService()

# Однократная проверка
service.check_emails()

# Результаты будут в Google Таблице и логе
```

---

**Все работает локально!** 🎉  
Никаких облачных API (кроме опционального Google Sheets).
