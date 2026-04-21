# Руководство по проверке лабораторных работ MikroTik RouterOS

## Поддерживаемые форматы отчетов

### 1. TXT файлы с export конфигурации
Студенты могут присылать вывод команды `export` из MikroTik:
```
/interface print
/ip address print  
/ip route print
```

**Что проверяется:**
- Наличие команд настройки интерфейсов
- Корректность IP адресов и масок
- Наличие статических маршрутов (для лаб >= 2)
- Использование safe mode

### 2. Скриншоты (PNG, JPG)
Студенты могут присылать скриншоты:
- Топология сети из GNS3
- Вывод команд в терминале WinBox
- Результаты ping/traceroute
- Интерфейс RouterOS

**Требования к установке OCR:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-rus tesseract-ocr-eng

# macOS
brew install tesseract

# После установки пакетов Python:
pip install pytesseract pillow
```

### 3. PDF/DOCX документы
Традиционные отчеты в формате Word или PDF с:
- Текстовым описанием
- Вставленными скриншотами
- Выводами команд

## Критерии оценки MikroTik работ

### Лабораторная №1 - Базовая настройка
**Обязательные элементы:**
- [ ] Reset конфигурации (`system reset-configuration`)
- [ ] Использование safe mode (`<SAFE>`)
- [ ] Настройка hostname (`system identity set name=...`)
- [ ] Настройка IP адресов на интерфейсах
- [ ] Проверка командой `ip address print`

**Пример правильной конфигурации:**
```
[admin@left] > ip address print
Flags: X - disabled, I - invalid, D - dynamic
 #   ADDRESS            NETWORK         INTERFACE
 0   192.168.0.254/24   192.168.0.0     ether3
 1   172.16.20.254/24   172.16.20.0     ether2
 2   172.16.10.254/24   172.16.10.0     ether1
```

### Лабораторная №2 - Статическая маршрутизация
**Дополнительные требования:**
- [ ] Все требования из Лаб 1
- [ ] Настройка минимум 2 статических маршрутов
- [ ] Проверка маршрутов (`ip route print`)
- [ ] Тестирование ping между подсетями
- [ ] Скриншоты топологии и результатов ping

**Пример статических маршрутов:**
```
[admin@left] > ip route print
Flags: X - disabled, A - active, D - dynamic,
C - connect, S - static
 #      DST-ADDRESS        GATEWAY            DISTANCE
 0 A S  10.11.12.0/24      192.168.0.253             1
 1 A S  10.11.13.0/24      192.168.0.253             1
```

## Обнаружение плагиата

Система автоматически проверяет работы на плагиат:

### Методы обнаружения:
1. **Сравнение конфигураций** - хэширование структуры команд
2. **Текстовая схожесть** - Jaccard similarity нормализованного текста
3. **Сравнение IP адресов** - по количеству и маскам (не по значениям)
4. **Анализ скриншотов** - OCR + сравнение распознанного текста

### Пороговые значения:
- **85%+ схожесть** - помечается как возможный плагиат
- LLM получает предупреждение и снижает оценку

### Что считается плагиатом:
- Идентичные конфигурации (все IP и маршруты совпадают)
- Одинаковые скриншоты (распознанный текст совпадает)
- Копирование отчета у одногруппников

## Примеры отчетов

### Хороший отчет (TXT):
```
Лабораторная работа №2
Студент: Иванов Иван, группа ПИ-202

Настройка левого роутера:
/system identity set name=left

interface print
# Видим ether1, ether2, ether3

ip address add address=172.16.10.254/24 interface=ether1
ip address add address=172.16.20.254/24 interface=ether2
ip address add address=192.168.0.254/24 interface=ether3

ip route add dst-address=10.11.12.0/24 gateway=192.168.0.253
ip route add dst-address=10.11.13.0/24 gateway=192.168.0.253

Проверка:
ping 10.11.12.1
# 64 bytes from 10.11.12.1: icmp_seq=1 ttl=64 time=2.3 ms

Вывод: Настроил статическую маршрутизацию, пинг работает.
```

### Плохой отчет (признаки):
- ❌ Только скриншот без текстового описания
- ❌ Нет вывода команд `print`
- ❌ Отсутствуют статические маршруты (для Лаб 2)
- ❌ Нет тестирования ping
- ❌ Текст скопирован из примера без изменений

## Настройка системы

### 1. Установка зависимостей
```bash
cd lab_checker
pip install -r requirements.txt
```

### 2. Установка Tesseract OCR
```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-rus

# Проверка
tesseract --version
```

### 3. Конфигурация (.env файл)
```ini
# IMAP почта
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your.email@gmail.com
IMAP_PASSWORD=your_app_password

# Ollama LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Google Sheets (опционально)
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_CREDENTIALS_FILE=config/credentials.json
```

### 4. Запуск модели Ollama
```bash
# Установка llama3.2
ollama pull llama3.2

# Проверка
ollama run llama3.2 "Привет!"
```

## Troubleshooting

### OCR не распознает текст
```bash
# Проверьте установку tesseract
which tesseract
tesseract --list-langs

# Должны быть: eng, rus
# Если нет - установите языковые пакеты
```

### Модель LLM недоступна
```bash
# Проверьте статус Ollama
ollama list

# Если пусто - скачайте модель
ollama pull llama3.2

# Перезапустите сервис
sudo systemctl restart ollama
```

### Плагиат не обнаруживается
- Проверьте порог в main.py: `PlagiarismDetector(similarity_threshold=0.85)`
- Уменьшите до 0.7 для более строгой проверки
