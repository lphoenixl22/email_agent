"""
SMTP клиент для отправки писем студентам с результатами проверки
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Optional, List
import os

logger = logging.getLogger(__name__)


class EmailSender:
    """Клиент для отправки писем через SMTP"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 username: str, password: str, use_tls: bool = True):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.server = None
    
    def connect(self) -> bool:
        """Подключение к SMTP серверу"""
        try:
            if self.use_tls:
                self.server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                self.server.starttls()
            else:
                self.server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            
            self.server.login(self.username, self.password)
            logger.info(f"Успешное подключение к SMTP серверу {self.smtp_server}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к SMTP серверу: {e}")
            return False
    
    def disconnect(self):
        """Отключение от SMTP сервера"""
        if self.server:
            self.server.quit()
            logger.info("Отключение от SMTP сервера")
    
    def send_grade_email(self, student_email: str, student_name: str, 
                         lab_number: int, score: float, max_score: float,
                         comment: str, criteria_scores: Optional[Dict] = None,
                         attachments: Optional[List[str]] = None) -> bool:
        """
        Отправка письма студенту с результатом проверки лабораторной работы
        
        Args:
            student_email: Email студента
            student_name: ФИО студента
            lab_number: Номер лабораторной работы
            score: Полученная оценка
            max_score: Максимальная оценка
            comment: Комментарий преподавателя
            criteria_scores: Оценки по критериям (опционально)
            attachments: Пути к файлам для вложения (опционально)
            
        Returns:
            True если письмо успешно отправлено
        """
        try:
            # Создание сообщения
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Результат проверки лабораторной работы №{lab_number}"
            msg['From'] = self.username
            msg['To'] = student_email
            
            # Формирование текста письма
            text_content = self._build_email_text(
                student_name, lab_number, score, max_score, 
                comment, criteria_scores
            )
            
            # Формирование HTML версии письма
            html_content = self._build_email_html(
                student_name, lab_number, score, max_score,
                comment, criteria_scores
            )
            
            # Добавление текстовой и HTML частей
            part_text = MIMEText(text_content, 'plain', 'utf-8')
            part_html = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part_text)
            msg.attach(part_html)
            
            # Добавление вложений
            if attachments:
                for filepath in attachments:
                    self._attach_file(msg, filepath)
            
            # Отправка письма
            self.server.send_message(msg)
            
            logger.info(f"Письмо с оценкой отправлено студенту {student_email} "
                       f"(лабораторная №{lab_number}, оценка: {score}/{max_score})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки письма студенту {student_email}: {e}")
            return False
    
    def _build_email_text(self, student_name: str, lab_number: int,
                          score: float, max_score: float, comment: str,
                          criteria_scores: Optional[Dict]) -> str:
        """Создание текстовой версии письма"""
        text = f"""Здравствуйте, {student_name}!

Ваша лабораторная работа №{lab_number} проверена.

РЕЗУЛЬТАТ:
Оценка: {score} из {max_score}

ПОДРОБНЫЙ КОММЕНТАРИЙ:
{comment}
"""
        
        if criteria_scores:
            text += "\n\nОЦЕНКИ ПО КРИТЕРИЯМ:\n"
            for criterion, value in criteria_scores.items():
                text += f"- {criterion}: {value}\n"
        
        text += """
С уважением,
Система автоматической проверки лабораторных работ
"""
        return text
    
    def _build_email_html(self, student_name: str, lab_number: int,
                          score: float, max_score: float, comment: str,
                          criteria_scores: Optional[Dict]) -> str:
        """Создание HTML версии письма"""
        # Определение цвета оценки
        percentage = (score / max_score * 100) if max_score > 0 else 0
        if percentage >= 80:
            color = "#28a745"  # зеленый
        elif percentage >= 60:
            color = "#ffc107"  # желтый
        else:
            color = "#dc3545"  # красный
        
        html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .greeting {{ font-size: 18px; margin-bottom: 10px; }}
        .result-box {{ background-color: #f8f9fa; border-left: 4px solid {color}; padding: 15px; margin: 20px 0; }}
        .score {{ font-size: 24px; font-weight: bold; color: {color}; }}
        .comment {{ background-color: #fff; border: 1px solid #dee2e6; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .criteria {{ margin-top: 20px; }}
        .criteria-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="greeting">Здравствуйте, {student_name}!</div>
            <div>Ваша лабораторная работа №{lab_number} проверена.</div>
        </div>
        
        <div class="result-box">
            <div>РЕЗУЛЬТАТ ПРОВЕРКИ:</div>
            <div class="score">{score} из {max_score}</div>
        </div>
        
        <div class="comment">
            <strong>ПОДРОБНЫЙ КОММЕНТАРИЙ:</strong><br>
            {comment.replace(chr(10), '<br>')}
        </div>
"""
        
        if criteria_scores:
            html += """
        <div class="criteria">
            <strong>ОЦЕНКИ ПО КРИТЕРИЯМ:</strong>
"""
            for criterion, value in criteria_scores.items():
                html += f"""
            <div class="criteria-item">
                <strong>{criterion}:</strong> {value}
            </div>
"""
            html += """
        </div>
"""
        
        html += """
        <div class="footer">
            С уважением,<br>
            Система автоматической проверки лабораторных работ
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Добавление вложения к письму"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Файл для вложения не найден: {filepath}")
                return
            
            with open(filepath, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            
            filename = os.path.basename(filepath)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            msg.attach(part)
            logger.debug(f"Добавлено вложение: {filename}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления вложения {filepath}: {e}")
    
    def test_connection(self) -> bool:
        """Тестирование подключения к SMTP серверу"""
        try:
            if not self.server:
                if not self.connect():
                    return False
            
            # Тестовая отправка самому себе
            msg = MIMEMultipart()
            msg['Subject'] = "Тест подключения SMTP"
            msg['From'] = self.username
            msg['To'] = self.username
            msg.attach(MIMEText("Это тестовое письмо для проверки подключения к SMTP серверу.", 'plain', 'utf-8'))
            
            self.server.send_message(msg)
            logger.info("Тестовое письмо успешно отправлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка тестирования SMTP подключения: {e}")
            return False
