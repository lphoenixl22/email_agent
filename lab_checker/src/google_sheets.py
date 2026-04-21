"""
Интеграция с Google Таблицами для записи оценок
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Клиент для работы с Google Таблицами"""
    
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Инициализация сервиса Google Sheets"""
        try:
            from google.oauth2.credentials import Credentials
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            import os
            
            # Проверка файла учетных данных
            if not os.path.exists(self.credentials_file):
                logger.error(f"Файл учетных данных не найден: {self.credentials_file}")
                raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
            
            # Загрузка учетных данных
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Попытка загрузки из service account JSON
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_file, scopes=scopes)
            except Exception:
                # Если не получилось, пробуем другой формат
                logger.warning("Не удалось загрузить service account, пробуем OAuth")
                raise
            
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets сервис инициализирован")
            
        except ImportError as e:
            logger.error(f"Отсутствуют необходимые библиотеки: {e}")
            logger.info("Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            raise
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets: {e}")
            raise
    
    def append_grade(self, student_info: Dict, analysis_result: Dict, 
                    worksheet_name: str = "Оценки") -> bool:
        """
        Добавление оценки в таблицу
        
        Args:
            student_info: Информация о студенте
            analysis_result: Результат анализа LLM
            worksheet_name: Название листа
            
        Returns:
            True если успешно
        """
        try:
            sheet = self.service.spreadsheets()
            
            # Подготовка данных для записи
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            row_data = [
                now,  # Дата
                student_info.get('student_name', 'Неизвестно'),  # ФИО
                student_info.get('group', ''),  # Группа
                student_info.get('email', ''),  # Email
                f"Лабораторная {student_info.get('lab_number', 'N/A')}",  # Работа
                analysis_result.get('score', 0),  # Оценка
                f"{analysis_result.get('score', 0)}/{analysis_result.get('max_score', 10)}",  # Баллы
                analysis_result.get('comment', '')[:500],  # Комментарий (обрезанный)
                'Проверено' if analysis_result.get('success') else 'Ошибка'  # Статус
            ]
            
            # Получение текущего размера листа
            range_name = f"{worksheet_name}!A:A"
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Если таблица пустая, добавляем заголовок
            if next_row == 1:
                header = ['Дата', 'ФИО', 'Группа', 'Email', 'Работа', 'Оценка', 'Баллы', 'Комментарий', 'Статус']
                self._update_range(worksheet_name, 'A1:I1', [header])
                next_row = 2
            
            # Добавление новой строки
            range_name = f"{worksheet_name}!A{next_row}"
            self._update_range(worksheet_name, f"A{next_row}:I{next_row}", [row_data])
            
            logger.info(f"Добавлена оценка для {student_info.get('student_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка записи в Google Sheets: {e}")
            return False
    
    def _update_range(self, worksheet_name: str, range_name: str, values: List[List]):
        """Обновление диапазона ячеек"""
        full_range = f"{self.spreadsheet_id}!{worksheet_name}!{range_name}"
        
        body = {
            'values': values
        }
        
        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{worksheet_name}!{range_name.split('!')[1] if '!' in range_name else range_name}",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return result
    
    def get_grades(self, worksheet_name: str = "Оценки", 
                   lab_number: Optional[int] = None) -> List[Dict]:
        """
        Получение оценок из таблицы
        
        Args:
            worksheet_name: Название листа
            lab_number: Номер лабораторной для фильтрации
            
        Returns:
            Список записей с оценками
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=worksheet_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return []
            
            # Первая строка - заголовки
            headers = values[0] if values else []
            
            grades = []
            for row in values[1:]:
                if len(row) < len(headers):
                    row.extend([''] * (len(headers) - len(row)))
                
                record = dict(zip(headers, row))
                
                # Фильтрация по номеру лабораторной
                if lab_number is not None:
                    work_field = record.get('Работа', '')
                    if str(lab_number) not in work_field:
                        continue
                
                grades.append(record)
            
            return grades
            
        except Exception as e:
            logger.error(f"Ошибка чтения из Google Sheets: {e}")
            return []
    
    def find_student_record(self, student_email: str, lab_number: int,
                           worksheet_name: str = "Оценки") -> Optional[Dict]:
        """Поиск существующей записи студента"""
        grades = self.get_grades(worksheet_name)
        
        for record in grades:
            email_match = student_email.lower() in record.get('Email', '').lower()
            lab_match = str(lab_number) in record.get('Работа', '')
            
            if email_match and lab_match:
                return record
        
        return None
    
    def update_grade(self, student_email: str, lab_number: int, 
                    new_score: float, comment: str = "",
                    worksheet_name: str = "Оценки") -> bool:
        """Обновление существующей оценки"""
        try:
            grades = self.get_grades(worksheet_name)
            
            for i, record in enumerate(grades, start=2):  # Начинаем с 2 (после заголовка)
                email_match = student_email.lower() in record.get('Email', '').lower()
                lab_match = str(lab_number) in record.get('Работа', '')
                
                if email_match and lab_match:
                    # Обновление ячейки с оценкой
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{worksheet_name}!F{i}",
                        valueInputOption='USER_ENTERED',
                        body={'values': [[new_score]]}
                    ).execute()
                    
                    # Обновление комментария
                    if comment:
                        self.service.spreadsheets().values().update(
                            spreadsheetId=self.spreadsheet_id,
                            range=f"{worksheet_name}!H{i}",
                            valueInputOption='USER_ENTERED',
                            body={'values': [[comment[:500]]]}
                        ).execute()
                    
                    logger.info(f"Обновлена оценка для {student_email}, лаб {lab_number}")
                    return True
            
            logger.warning(f"Запись не найдена для {student_email}, лаб {lab_number}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка обновления оценки: {e}")
            return False
    
    def create_worksheet_if_not_exists(self, worksheet_name: str) -> bool:
        """Создание нового листа если он не существует"""
        try:
            # Получение списка листов
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            existing_names = [s['properties']['title'] for s in sheets]
            
            if worksheet_name in existing_names:
                logger.info(f"Лист '{worksheet_name}' уже существует")
                return True
            
            # Создание нового листа
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': worksheet_name
                    }
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Создан лист '{worksheet_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания листа: {e}")
            return False


class MockGoogleSheetsClient:
    """Моковый клиент для тестирования без Google API"""
    
    def __init__(self, *args, **kwargs):
        self.data = []
        logger.warning("Используется моковый клиент Google Sheets (данные не сохраняются)")
    
    def append_grade(self, student_info: Dict, analysis_result: Dict,
                    worksheet_name: str = "Оценки") -> bool:
        record = {
            'timestamp': datetime.now().isoformat(),
            'student': student_info,
            'analysis': analysis_result,
            'worksheet': worksheet_name
        }
        self.data.append(record)
        logger.info(f"[MOCK] Добавлена оценка: {student_info.get('student_name')} - {analysis_result.get('score')}")
        return True
    
    def get_grades(self, worksheet_name: str = "Оценки",
                   lab_number: Optional[int] = None) -> List[Dict]:
        return self.data
    
    def create_worksheet_if_not_exists(self, worksheet_name: str) -> bool:
        return True
