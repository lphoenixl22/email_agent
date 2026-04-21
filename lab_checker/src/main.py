"""
Основной модуль сервиса проверки лабораторных работ
"""
import os
import sys
import time
import signal
import logging
from typing import Optional
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import yaml

from email_client import EmailClient
from parser import ReportParser
from llm_analyzer import LLMAnalyzer
from lab_manager import LabManager
from google_sheets import GoogleSheetsClient, MockGoogleSheetsClient
from plagiarism_detector import PlagiarismDetector

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lab_checker.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class LabCheckerService:
    """Основной сервис проверки лабораторных работ"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Загрузка переменных окружения
        load_dotenv()
        
        # Инициализация компонентов
        self.email_client = None
        self.parser = ReportParser()
        self.llm_analyzer = None
        self.lab_manager = LabManager()
        self.sheets_client = None
        self.plagiarism_detector = PlagiarismDetector(similarity_threshold=0.85)
        
        self._init_components()
        
        # Флаг остановки
        self.running = False
    
    def _load_config(self) -> dict:
        """Загрузка конфигурации"""
        config_file = Path(config_path if 'config_path' in locals() else "config/config.yaml")
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        # Конфигурация по умолчанию
        return {
            'email': {'check_interval': 60},
            'llm': {'host': 'http://localhost:11434', 'model': 'llama3.2'},
            'google_sheets': {'spreadsheet_id': '', 'credentials_file': 'config/credentials.json'},
            'labs': {'directory': 'config/labs'}
        }
    
    def _init_components(self):
        """Инициализация компонентов сервиса"""
        
        # Инициализация почтового клиента
        imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        imap_port = int(os.getenv('IMAP_PORT', '993'))
        imap_username = os.getenv('IMAP_USERNAME', '')
        imap_password = os.getenv('IMAP_PASSWORD', '')
        
        if imap_username and imap_password:
            self.email_client = EmailClient(
                server=imap_server,
                port=imap_port,
                username=imap_username,
                password=imap_password
            )
            logger.info("Почтовый клиент инициализирован")
        else:
            logger.warning("IMAP учетные данные не настроены")
        
        # Инициализация LLM анализатора
        llm_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        llm_model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        
        try:
            self.llm_analyzer = LLMAnalyzer(host=llm_host, model=llm_model)
            logger.info(f"LLM анализатор инициализирован (модель: {llm_model})")
        except Exception as e:
            logger.error(f"Ошибка инициализации LLM: {e}")
            raise
        
        # Инициализация Google Sheets клиента
        sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'config/credentials.json')
        
        if sheet_id and Path(creds_file).exists():
            try:
                self.sheets_client = GoogleSheetsClient(
                    credentials_file=creds_file,
                    spreadsheet_id=sheet_id
                )
                logger.info("Google Sheets клиент инициализирован")
            except Exception as e:
                logger.warning(f"Google Sheets недоступен, используется моковый режим: {e}")
                self.sheets_client = MockGoogleSheetsClient()
        else:
            logger.warning("Google Sheets не настроен, используется моковый режим")
            self.sheets_client = MockGoogleSheetsClient()
    
    def process_email(self, email_data: dict) -> bool:
        """Обработка одного письма"""
        try:
            logger.info(f"Обработка письма: {email_data.get('subject', 'Без темы')}")
            
            # Парсинг информации о студенте
            student_info = self.parser.parse_email(email_data)
            
            if not student_info.get('lab_number'):
                logger.warning("Не удалось определить номер лабораторной работы")
                return False
            
            logger.info(f"Студент: {student_info.get('student_name')}, "
                       f"Группа: {student_info.get('group')}, "
                       f"Лабораторная: {student_info.get('lab_number')}")
            
            # Извлечение текста отчета из вложений
            report_text = ""
            for attachment in email_data.get('attachments', []):
                text = self.parser.extract_report_text(attachment)
                if text:
                    report_text += text + "\n"
            
            # Если нет вложений, пробуем использовать тело письма
            if not report_text and email_data.get('body'):
                report_text = email_data['body']
            
            if not report_text:
                logger.warning("Текст отчета не найден")
                return False
            
            # Валидация отчета
            validation = self.parser.validate_report(report_text, student_info['lab_number'])
            if not validation.get('valid'):
                logger.warning(f"Отчет не прошел валидацию: {validation.get('issues')}")
            
            # Получение конфигурации MikroTik (если есть)
            mikrotik_config = validation.get('mikrotik_config')
            
            # Добавление работы для проверки на плагиат
            student_id = student_info.get('email') or student_info.get('student_name', 'unknown')
            self.plagiarism_detector.add_submission(
                student_id=student_id,
                report_text=report_text,
                mikrotik_config=mikrotik_config
            )
            
            # Проверка на плагиат
            plagiarism_check = self.plagiarism_detector.check_plagiarism(student_id)
            if plagiarism_check.get('is_plagiarism'):
                logger.warning(f"⚠️ Обнаружен возможный плагиат! Студент: {student_id}")
                for match in plagiarism_check.get('matches', [])[:3]:
                    logger.warning(f"  - Схожесть с {match['student_id']}: {match['similarity']*100:.1f}% ({match['type']})")
                
                # Добавляем информацию о плагиате в анализ
                plagiarism_comment = f"\n\n⚠️ ВОЗМОЖЕН ПЛАГИАТ! Найдено совпадений: {len(plagiarism_check['matches'])}. " \
                                   f"Максимальная схожесть: {plagiarism_check['similarity_score']*100:.1f}%"
                # Сохраняем для передачи в LLM
                student_info['plagiarism_warning'] = plagiarism_comment
            
            # Загрузка требований к лабораторной
            lab_requirements = self.lab_manager.load_lab_requirements(
                student_info['lab_number']
            )
            
            # Анализ отчета с помощью LLM
            analysis_result = self.llm_analyzer.analyze_report(
                report_text=report_text,
                lab_requirements=lab_requirements,
                student_info=student_info
            )
            
            if not analysis_result.get('success'):
                logger.error("Ошибка анализа отчета")
                return False
            
            logger.info(f"Оценка: {analysis_result.get('score')}/{analysis_result.get('max_score')}")
            logger.info(f"Комментарий: {analysis_result.get('comment')[:100]}...")
            
            # Запись оценки в Google Таблицу
            if self.sheets_client:
                self.sheets_client.append_grade(student_info, analysis_result)
            
            # Пометка письма как прочитанного
            if self.email_client and self.config.get('email', {}).get('mark_as_read', True):
                self.email_client.mark_as_read(email_data['id'])
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки письма: {e}", exc_info=True)
            return False
    
    def check_emails(self):
        """Проверка новых писем"""
        if not self.email_client:
            logger.warning("Почтовый клиент не инициализирован")
            return
        
        try:
            # Подключение к почтовому серверу
            if not self.email_client.connection:
                if not self.email_client.connect():
                    return
            
            # Получение непрочитанных писем
            emails = self.email_client.get_unread_emails()
            
            if not emails:
                logger.debug("Нет новых писем")
                return
            
            logger.info(f"Найдено {len(emails)} новых писем")
            
            # Обработка каждого письма
            for email_data in emails:
                self.process_email(email_data)
                
        except Exception as e:
            logger.error(f"Ошибка проверки почты: {e}")
            # Попытка переподключения
            if self.email_client:
                self.email_client.disconnect()
    
    def run(self):
        """Запуск основного цикла сервиса"""
        logger.info("=" * 50)
        logger.info("Запуск сервиса проверки лабораторных работ")
        logger.info("=" * 50)
        
        # Проверка доступности модели
        if self.llm_analyzer and not self.llm_analyzer.check_model_availability():
            logger.warning("Модель LLM может быть недоступна")
        
        self.running = True
        
        # Обработчик сигналов для корректной остановки
        def signal_handler(sig, frame):
            logger.info("Получен сигнал остановки")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        check_interval = self.config.get('email', {}).get('check_interval', 60)
        
        logger.info(f"Интервал проверки почты: {check_interval} секунд")
        logger.info("Сервис запущен. Нажмите Ctrl+C для остановки.")
        
        while self.running:
            try:
                self.check_emails()
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки: {e}")
            
            # Ожидание до следующей проверки
            for _ in range(check_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        # Остановка
        logger.info("Остановка сервиса...")
        if self.email_client:
            self.email_client.disconnect()
        
        logger.info("Сервис остановлен")


def main():
    """Точка входа"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Сервис проверки лабораторных работ')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Путь к файлу конфигурации')
    parser.add_argument('--once', action='store_true',
                       help='Выполнить одну проверку и выйти')
    
    args = parser.parse_args()
    
    try:
        service = LabCheckerService(config_path=args.config)
        
        if args.once:
            logger.info("Режим однократной проверки")
            service.check_emails()
        else:
            service.run()
            
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
