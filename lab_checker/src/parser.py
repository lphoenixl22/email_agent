"""
Парсер писем и извлечение текста из отчетов
Поддержка: TXT, PDF, DOCX, скриншоты (PNG/JPG) с OCR
"""
import re
import os
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ReportParser:
    """Парсер для извлечения данных из писем и отчетов"""
    
    def __init__(self):
        # Паттерны для определения номера лабораторной
        self.lab_patterns = [
            r'лабораторная\s+работа?\s*[№#]?\s*(\d+)',
            r'лаб\.?\s*[№#]?\s*(\d+)',
            r'lr[-_]?(\d+)',
            r'lab[-_]?(\d+)',
            r'работа\s*[№#]?\s*(\d+)',
            r'mikrotik\s+(?:lab|laboratory|работа)?\s*(\d+)?',
        ]
        
        # Паттерны для извлечения ФИО
        self.name_patterns = [
            r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)',
            r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.?\s*[А-ЯЁ]\.?)',
        ]
        
        # Паттерны для извлечения группы
        self.group_patterns = [
            r'группа?\s*([А-ЯЁ]{1,4}[-_]?\d{2,4})',
            r'([А-ЯЁ]{1,4}[-_]?\d{2,4})',
        ]
        
        # Паттерны MikroTik команд
        self.mikrotik_patterns = {
            'interface': r'interface\s+(?:print|add|remove|set)',
            'ip_address': r'ip\s+address\s+(?:print|add|remove)',
            'ip_route': r'ip\s+route\s+(?:print|add|remove)',
            'system_identity': r'system\s+identity\s+set',
            'safe_mode': r'<SAFE>',
            'ping': r'ping\s+\d+\.\d+\.\d+\.\d+',
        }
    
    def parse_email(self, email_data: Dict) -> Dict:
        """Извлечение информации из письма"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        from_addr = email_data.get('from', '')
        
        # Объединяем тему и тело для анализа
        text = f"{subject}\n{body}"
        
        # Извлечение номера лабораторной
        lab_number = self.extract_lab_number(text)
        
        # Извлечение ФИО
        student_name = self.extract_student_name(text, from_addr)
        
        # Извлечение группы
        group = self.extract_group(text)
        
        # Извлечение email
        email_address = self.extract_email(from_addr)
        
        return {
            'lab_number': lab_number,
            'student_name': student_name,
            'group': group,
            'email': email_address,
            'subject': subject,
            'email_id': email_data.get('id'),
        }
    
    def extract_lab_number(self, text: str) -> Optional[int]:
        """Извлечение номера лабораторной работы"""
        text_lower = text.lower()
        
        for pattern in self.lab_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    num = match.group(1)
                    if num:
                        return int(num)
                except (ValueError, IndexError):
                    continue
        
        # Если не найдено в тексте, пробуем определить по контексту MikroTik
        if 'mikrotik' in text_lower or 'routeros' in text_lower:
            logger.info("Обнаружен отчет по MikroTik, номер лабораторной будет определен LLM")
            return 1  # Значение по умолчанию
        
        logger.warning(f"Не удалось определить номер лабораторной из текста: {text[:100]}")
        return None
    
    def extract_student_name(self, text: str, from_addr: str) -> Optional[str]:
        """Извлечение ФИО студента"""
        # Сначала пробуем найти в тексте
        for pattern in self.name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # Если не найдено, пробуем извлечь из адреса отправителя
        name_match = re.match(r'^([^<]+)', from_addr)
        if name_match:
            name = name_match.group(1).strip()
            if len(name) > 3:
                return name
        
        return None
    
    def extract_group(self, text: str) -> Optional[str]:
        """Извлечение номера группы"""
        text_lower = text.lower()
        
        for pattern in self.group_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def extract_email(self, from_addr: str) -> str:
        """Извлечение email адреса"""
        match = re.search(r'<([^>]+)>', from_addr)
        if match:
            return match.group(1)
        return from_addr.strip()
    
    def extract_report_text(self, attachment: Dict) -> Optional[str]:
        """Извлечение текста из файла отчета"""
        filepath = attachment.get('filepath')
        content_type = attachment.get('content_type', '')
        filename = attachment.get('filename', '').lower()
        
        if not filepath or not os.path.exists(filepath):
            logger.error(f"Файл не найден: {filepath}")
            return None
        
        try:
            # Определение типа файла по расширению
            if filename.endswith('.pdf'):
                return self._extract_from_pdf(filepath)
            elif filename.endswith('.docx'):
                return self._extract_from_docx(filepath)
            elif filename.endswith('.txt'):
                return self._extract_from_txt(filepath)
            elif filename.endswith('.md'):
                return self._extract_from_txt(filepath)
            elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                return self._extract_from_image(filepath)
            else:
                # Пытаемся определить по content-type или прочитать как текст
                if 'pdf' in content_type:
                    return self._extract_from_pdf(filepath)
                elif 'word' in content_type or 'docx' in content_type:
                    return self._extract_from_docx(filepath)
                elif 'image' in content_type:
                    return self._extract_from_image(filepath)
                else:
                    return self._extract_from_txt(filepath)
                    
        except Exception as e:
            logger.error(f"Ошибка извлечения текста из {filepath}: {e}")
            return None
    
    def _extract_from_image(self, filepath: str) -> str:
        """Извлечение текста из изображения через OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            logger.info(f"Обработка изображения через OCR: {filepath}")
            
            # Открываем изображение
            img = Image.open(filepath)
            
            # Распознавание текста (русский + английский)
            text = pytesseract.image_to_string(img, lang='rus+eng')
            
            logger.info(f"OCR распознал {len(text)} символов")
            return text.strip()
            
        except ImportError as e:
            logger.warning(f"pytesseract или PIL не установлены: {e}")
            logger.warning("Установите: pip install pytesseract pillow и tesseract-ocr")
            return f"[Изображение: {filepath}] - требуется OCR"
        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return f"[Ошибка обработки изображения: {e}]"
    
    def _extract_from_pdf(self, filepath: str) -> str:
        """Извлечение текста из PDF"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            if not text.strip():
                logger.warning("PDF не содержит текстового слоя, требуется OCR")
                # Здесь можно добавить обработку PDF с изображениями
                return "[PDF без текстового слоя - требуются скриншоты]"
            
            return text.strip()
        except ImportError:
            logger.warning("PyPDF2 не установлен, пробуем альтернативный метод")
            return self._extract_from_txt(filepath)
        except Exception as e:
            logger.error(f"Ошибка чтения PDF: {e}")
            raise
    
    def _extract_from_docx(self, filepath: str) -> str:
        """Извлечение текста из DOCX"""
        try:
            from docx import Document
            doc = Document(filepath)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except ImportError:
            logger.warning("python-docx не установлен")
            raise
        except Exception as e:
            logger.error(f"Ошибка чтения DOCX: {e}")
            raise
    
    def _extract_from_txt(self, filepath: str) -> str:
        """Извлечение текста из TXT/MD файлов"""
        encodings = ['utf-8', 'cp1251', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read().strip()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Ошибка чтения файла ({encoding}): {e}")
                continue
        
        logger.error(f"Не удалось прочитать файл ни в одной кодировке: {filepath}")
        return ""
    
    def detect_mikrotik_config(self, text: str) -> Dict:
        """Обнаружение конфигурации MikroTik в тексте"""
        result = {
            'is_mikrotik': False,
            'commands_found': [],
            'interfaces': [],
            'ip_addresses': [],
            'routes': [],
            'has_safe_mode': False,
        }
        
        text_lower = text.lower()
        
        # Проверка на наличие команд MikroTik
        for cmd_type, pattern in self.mikrotik_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result['is_mikrotik'] = True
                result['commands_found'].append(cmd_type)
        
        # Извлечение интерфейсов
        interface_matches = re.findall(
            r'interface\s+(?:print.*?)?(?:ether\d+|wlan\d+|vlan\d+)',
            text, re.IGNORECASE | re.DOTALL
        )
        if interface_matches:
            result['interfaces'] = interface_matches
        
        # Извлечение IP адресов
        ip_matches = re.findall(
            r'(?:ip\s+address\s+add\s+)?address=(\d+\.\d+\.\d+\.\d+)(?:\s+|\s*/\s*)(\d+)?',
            text, re.IGNORECASE
        )
        if ip_matches:
            result['ip_addresses'] = [f"{ip[0]}/{ip[1] if ip[1] else '24'}" for ip in ip_matches]
        
        # Также ищем в выводе print
        ip_print_matches = re.findall(
            r'(\d+\.\d+\.\d+\.\d+/\d+)\s+\d+\.\d+\.\d+\.\d+\s+(ether\d+)',
            text
        )
        if ip_print_matches:
            result['ip_addresses'].extend([f"{ip[0]} ({ip[1]})" for ip in ip_print_matches])
        
        # Извлечение маршрутов
        route_matches = re.findall(
            r'ip\s+route\s+add\s+dst-address=(\d+\.\d+\.\d+\.\d+/\d+)\s+gateway=(\S+)',
            text, re.IGNORECASE
        )
        if route_matches:
            result['routes'] = [f"{r[0]} via {r[1]}" for r in route_matches]
        
        # Проверка safe mode
        if '<SAFE>' in text or 'safe mode' in text_lower:
            result['has_safe_mode'] = True
        
        return result
    
    def validate_report(self, report_text: str, lab_number: int) -> Dict:
        """Базовая валидация отчета перед отправкой в LLM"""
        issues = []
        
        if not report_text:
            issues.append("Текст отчета пуст")
            return {'valid': False, 'issues': issues}
        
        if len(report_text) < 50:
            issues.append("Текст отчета слишком короткий")
        
        # Специфичная проверка для MikroTik
        mikrotik_data = self.detect_mikrotik_config(report_text)
        
        if mikrotik_data['is_mikrotik']:
            # Для лабораторных по MikroTik проверяем наличие команд
            if len(mikrotik_data['commands_found']) < 2:
                issues.append("Мало команд MikroTik в отчете")
            
            if not mikrotik_data['ip_addresses']:
                issues.append("Не найдены настроенные IP адреса")
            
            if lab_number and lab_number >= 2 and not mikrotik_data['routes']:
                issues.append("Для лабораторной >= 2 не найдены статические маршруты")
        else:
            # Для обычных отчетов проверяем разделы
            required_sections = ['цель', 'задание', 'вывод']
            text_lower = report_text.lower()
            missing_sections = []
            
            for section in required_sections:
                if section not in text_lower:
                    missing_sections.append(section)
            
            if missing_sections:
                issues.append(f"Возможно отсутствуют разделы: {', '.join(missing_sections)}")
        
        return {
            'valid': len(issues) == 0 or len(issues) <= 1,
            'issues': issues,
            'word_count': len(report_text.split()),
            'mikrotik_config': mikrotik_data if mikrotik_data['is_mikrotik'] else None
        }
