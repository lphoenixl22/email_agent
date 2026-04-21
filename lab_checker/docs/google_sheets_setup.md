# Инструкция по настройке Google Sheets API

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Sheets API"
   - Нажмите "Enable"

## Шаг 2: Создание Service Account

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните информацию:
   - Service account name: `lab-checker`
   - Service account ID: будет создан автоматически
   - Description: `Сервис для проверки лабораторных работ`
4. Нажмите "Create and Continue"
5. Пропустите выбор ролей (или выберите "Editor")
6. Нажмите "Done"

## Шаг 3: Создание ключа доступа

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на email аккаунта
3. Перейдите во вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите тип ключа: **JSON**
6. Нажмите "Create"
7. Файл с ключом будет загружен автоматически
8. Переименуйте файл в `credentials.json` и поместите в папку `config/`

## Шаг 4: Предоставление доступа к таблице

1. Создайте новую Google Таблицу или откройте существующую
2. Нажмите кнопку "Share" (Поделиться) в правом верхнем углу
3. Вставьте email сервисного аккаунта (из файла credentials.json, поле `client_email`)
4. Предоставьте доступ на редактирование ("Editor")
5. Скопируйте ID таблицы из URL (между `/d/` и `/edit`)
   - Пример URL: `https://docs.google.com/spreadsheets/d/1ABC123xyz.../edit`
   - ID: `1ABC123xyz...`

## Шаг 5: Настройка переменных окружения

Добавьте в файл `.env`:

```bash
GOOGLE_SHEET_ID=ваш_id_таблицы
GOOGLE_CREDENTIALS_FILE=config/credentials.json
```

## Шаг 6: Проверка работы

Запустите сервис в режиме однократной проверки:

```bash
python src/main.py --once
```

В логах должно появиться сообщение об успешной инициализации Google Sheets клиента.

## Структура таблицы

Сервис автоматически создаст лист "Оценки" со следующими колонками:

| Дата | ФИО | Группа | Email | Работа | Оценка | Баллы | Комментарий | Статус |
|------|-----|--------|-------|--------|--------|-------|-------------|--------|

## Troubleshooting

### Ошибка "Credentials file not found"
- Убедитесь, что файл `credentials.json` находится в папке `config/`
- Проверьте путь в переменной `GOOGLE_CREDENTIALS_FILE`

### Ошибка "The caller does not have permission"
- Убедитесь, что сервисный аккаунт имеет доступ к таблице
- Проверьте, что вы скопировали правильный ID таблицы

### Ошибка "Google Sheets API has not been used"
- Включите Google Sheets API в Google Cloud Console
- Подождите несколько минут перед повторной попыткой
