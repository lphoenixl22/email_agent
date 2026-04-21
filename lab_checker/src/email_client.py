"""
IMAP клиент для получения писем с вложениями
"""
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailClient:
    """Клиент для работы с IMAP почтовым сервером"""
    
    def __init__(self, server: str, port: int, username: str, password: str):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        
    def connect(self) -> bool:
        """Подключение к почтовому серверу"""
        try:
            # Подключение по SSL
            self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            self.connection.login(self.username, self.password)
            self.connection.select('INBOX')
            logger.info(f"Успешное подключение к {self.server}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение от почтового сервера"""
        if self.connection:
            self.connection.close()
            self.connection.logout()
            logger.info("Отключение от почтового сервера")
    
    def get_unread_emails(self) -> List[Dict]:
        """Получение списка непрочитанных писем"""
        emails = []
        
        try:
            # Поиск непрочитанных писем
            status, messages = self.connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                return emails
            
            for msg_id in messages[0].split():
                email_data = self._fetch_email(msg_id)
                if email_data:
                    emails.append(email_data)
                    
        except Exception as e:
            logger.error(f"Ошибка получения писем: {e}")
        
        return emails
    
    def _fetch_email(self, msg_id: bytes) -> Optional[Dict]:
        """Извлечение данных письма"""
        try:
            status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
            
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Декодирование темы
            subject, encoding = decode_header(msg.get('Subject', ''))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8', errors='ignore')
            
            # Декодирование отправителя
            from_addr, encoding = decode_header(msg.get('From', ''))[0]
            if isinstance(from_addr, bytes):
                from_addr = from_addr.decode(encoding or 'utf-8', errors='ignore')
            
            # Получение даты
            date_str = msg.get('Date', '')
            
            # Извлечение тела письма и вложений
            body = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get_content_disposition())
                    
                    # Текстовая часть
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        except:
                            pass
                    
                    # Вложение
                    elif 'attachment' in content_disposition:
                        attachment = self._save_attachment(part)
                        if attachment:
                            attachments.append(attachment)
            else:
                # Простое письмо без вложений
                try:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = msg.get_payload(decode=True).decode(charset, errors='ignore')
                except:
                    pass
            
            return {
                'id': msg_id.decode(),
                'subject': subject,
                'from': from_addr,
                'date': date_str,
                'body': body,
                'attachments': attachments,
                'raw_msg': msg
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения письма {msg_id}: {e}")
            return None
    
    def _save_attachment(self, part) -> Optional[Dict]:
        """Сохранение вложения"""
        try:
            filename = part.get_filename()
            
            if not filename:
                filename = f"attachment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Декодирование имени файла
            filename, encoding = decode_header(filename)[0]
            if isinstance(filename, bytes):
                filename = filename.decode(encoding or 'utf-8', errors='ignore')
            
            # Создание временной директории
            temp_dir = os.environ.get('TEMP_DIR', '/tmp/lab_checker')
            os.makedirs(temp_dir, exist_ok=True)
            
            filepath = os.path.join(temp_dir, filename)
            
            # Сохранение файла
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            
            logger.info(f"Сохранено вложение: {filepath}")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'content_type': part.get_content_type()
            }
            
        except Exception as e:
            logger.error(f"Ошибка сохранения вложения: {e}")
            return None
    
    def mark_as_read(self, msg_id: str):
        """Пометка письма как прочитанного"""
        try:
            self.connection.store(msg_id.encode(), '+FLAGS', '\\Seen')
            logger.info(f"Письмо {msg_id} помечено как прочитанное")
        except Exception as e:
            logger.error(f"Ошибка пометки письма: {e}")
    
    def extract_email_address(self, from_string: str) -> str:
        """Извлечение email адреса из строки отправителя"""
        import re
        match = re.search(r'<([^>]+)>', from_string)
        if match:
            return match.group(1)
        return from_string.strip()
