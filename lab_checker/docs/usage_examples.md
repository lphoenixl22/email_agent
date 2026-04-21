# Примеры использования Lab Checker

## Быстрый старт

### 1. Установка зависимостей

```bash
cd lab_checker
pip install -r requirements.txt
```

### 2. Настройка

Скопируйте `.env.example` в `.env` и заполните:

```bash
# Для Gmail (нужен App Password)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your_email@gmail.com
IMAP_PASSWORD=your_app_password

# Ollama (локальная LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Google Sheets (опционально)
GOOGLE_SHEET_ID=ваш_id_таблицы
GOOGLE_CREDENTIALS_FILE=config/credentials.json
```

### 3. Запуск

```bash
# Постоянный режим (проверка каждые 60 секунд)
python src/main.py

# Однократная проверка
python src/main.py --once
```

## Сценарии использования

### Сценарий 1: Полная настройка с нуля

1. **Установите Ollama**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3.2
   ```

2. **Настройте почту**:
   - Для Gmail: создайте App Password в настройках аккаунта
   - Для других сервисов: используйте обычный пароль

3. **Настройте Google Sheets** (опционально):
   - Создайте Service Account
   - Скачайте credentials.json
   - Предоставьте доступ к таблице

4. **Запустите сервис**:
   ```bash
   python src/main.py
   ```

### Сценарий 2: Только локальное тестирование

Если хотите протестировать без реальной почты:

1. Создайте тестовое письмо в формате EML
2. Используйте парсер напрямую:

```python
from src.parser import ReportParser

parser = ReportParser()

# Тестовые данные
email_data = {
    'subject': 'Лабораторная работа №1 - Иванов Иван',
    'body': 'Прошу проверить мою работу',
    'from': 'Иванов Иван <ivanov@student.ru>',
    'attachments': [{'filepath': 'report.pdf', 'content_type': 'application/pdf'}]
}

student_info = parser.parse_email(email_data)
print(student_info)
```

### Сценарий 3: Интеграция с Git репозиторием

Загрузка требований из Git:

```python
from src.lab_manager import LabManager

lm = LabManager()

# Загрузка из публичного репозитория
lm.download_from_git(
    repo_url='https://github.com/username/lab-tasks.git',
    branch='main',
    target_path='requirements'
)

# Просмотр доступных работ
print(lm.list_available_labs())
```

## Формат писем от студентов

Студенты должны отправлять письма в следующем формате:

### Тема письма:
```
Лабораторная работа №{номер} - {Фамилия Имя Отчество}, группа {номер}
```

Примеры:
- `Лабораторная работа №1 - Иванов Иван Иванович, группа ПИ-201`
- `Лаб 2 Петров Петр, группа ИВТ-202`
- `LR-03 Сидоров Сидор, группа ПМ-203`

### Вложения:
- Отчет в формате PDF, DOCX или TXT
- Исходный код (опционально, если не в отчете)

### Тело письма:
Может содержать краткое сопроводительное сообщение.

## Настройка критериев оценки

Для каждой лабораторной работы создайте файл `config/labs/lab_{номер}.yaml`:

```yaml
lab_number: 1
description: "Разработка консольного приложения"

tasks:
  - "Изучить основы Python"
  - "Реализовать программу"
  - "Протестировать"

criteria:
  - name: "Выполнение задания"
    weight: 0.5
  - name: "Качество кода"
    weight: 0.3
  - name: "Документация"
    weight: 0.2

max_score: 10
min_passing_score: 6
```

## Мониторинг и логи

Логи сохраняются в файл `lab_checker.log`:

```bash
# Просмотр логов в реальном времени
tail -f lab_checker.log

# Поиск ошибок
grep ERROR lab_checker.log
```

## API для интеграции

### Прямой вызов анализатора:

```python
from src.llm_analyzer import LLMAnalyzer

analyzer = LLMAnalyzer(model='llama3.2')

result = analyzer.analyze_report(
    report_text="Текст отчета студента...",
    lab_requirements={'tasks': ['...'], 'criteria': [...]},
    student_info={'lab_number': 1, 'student_name': 'Иванов', 'group': 'ПИ-201'}
)

print(f"Оценка: {result['score']}/{result['max_score']}")
print(f"Комментарий: {result['comment']}")
```

### Работа с Google Sheets:

```python
from src.google_sheets import GoogleSheetsClient

client = GoogleSheetsClient(
    credentials_file='config/credentials.json',
    spreadsheet_id='your_sheet_id'
)

# Добавление оценки
client.append_grade(
    student_info={'student_name': 'Иванов', 'group': 'ПИ-201', 'lab_number': 1},
    analysis_result={'score': 8, 'max_score': 10, 'comment': 'Хорошая работа'}
)

# Получение оценок
grades = client.get_grades(lab_number=1)
for grade in grades:
    print(grade)
```

## Устранение проблем

### Письма не загружаются
- Проверьте логин/пароль IMAP
- Для Gmail используйте App Password, а не основной пароль
- Проверьте настройки безопасности почтового сервиса

### Ollama не отвечает
```bash
# Проверьте статус
ollama list

# Перезапустите сервис
ollama serve
```

### Ошибки Google Sheets
- Проверьте наличие файла credentials.json
- Убедитесь, что Service Account имеет доступ к таблице
- Проверьте ID таблицы в URL

### Модель выдает некорректные оценки
- Попробуйте другую модель (mistral, saiga)
- Настройте prompt в llm_analyzer.py
- Добавьте больше примеров в требования к лабам
