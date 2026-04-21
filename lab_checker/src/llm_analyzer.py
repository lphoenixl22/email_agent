"""
Анализ отчетов с помощью локальной LLM (Ollama)
"""
import json
from typing import Dict, Optional, List
import logging
import os

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Анализ студенческих отчетов с помощью локальной LLM"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host
        self.model = model
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента Ollama"""
        try:
            import ollama
            self.client = ollama.Client(host=self.host)
            
            # Проверка доступности модели
            try:
                self.client.chat(model=self.model, messages=[{'role': 'user', 'content': 'test'}])
                logger.info(f"Модель {self.model} доступна")
            except Exception as e:
                logger.warning(f"Модель {self.model} может быть недоступна: {e}")
                
        except ImportError:
            logger.error("Библиотека ollama не установлена. Установите: pip install ollama")
            raise
    
    def analyze_report(self, report_text: str, lab_requirements: Dict, 
                      student_info: Dict) -> Dict:
        """
        Анализ отчета студента
        
        Args:
            report_text: Текст отчета
            lab_requirements: Требования к лабораторной работе
            student_info: Информация о студенте
            
        Returns:
            Словарь с оценкой и комментарием
        """
        
        # Формирование промпта для анализа
        prompt = self._build_prompt(report_text, lab_requirements, student_info)
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': self._get_system_prompt()
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.3,
                    'max_tokens': 1024
                }
            )
            
            result_text = response['message']['content']
            
            # Парсинг ответа LLM
            analysis = self._parse_llm_response(result_text)
            
            return {
                'success': True,
                'score': analysis.get('score', 0),
                'max_score': analysis.get('max_score', 10),
                'comment': analysis.get('comment', ''),
                'criteria_scores': analysis.get('criteria_scores', {}),
                'raw_response': result_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе отчета: {e}")
            return {
                'success': False,
                'score': 0,
                'max_score': 10,
                'comment': f"Ошибка анализа: {str(e)}",
                'criteria_scores': {},
                'raw_response': ''
            }
    
    def _get_system_prompt(self) -> str:
        """Системный промпт для LLM"""
        return """Ты - преподаватель, который проверяет студенческие лабораторные работы.
Твоя задача - объективно оценить отчет студента по заданным критериям.

Важные правила:
1. Будь строгим, но справедливым
2. Оценивай по 10-балльной шкале
3. Давай развернутый комментарий с указанием достоинств и недостатков
4. В ответе обязательно укажи:
   - Итоговую оценку (число от 0 до 10)
   - Максимально возможную оценку (обычно 10)
   - Подробный комментарий на русском языке
   - Оценки по отдельным критериям (если указаны)

Формат ответа должен быть следующим:
ОЦЕНКА: <число от 0 до 10>
МАКС_ОЦЕНКА: <максимальный балл>
КОММЕНТАРИЙ: <текст комментария>
КРИТЕРИИ: <JSON объект с оценками по критериям>
"""
    
    def _build_prompt(self, report_text: str, lab_requirements: Dict, 
                     student_info: Dict) -> str:
        """Построение промпта для анализа"""
        
        lab_number = student_info.get('lab_number', 'N/A')
        student_name = student_info.get('student_name', 'Неизвестно')
        group = student_info.get('group', 'N/A')
        
        requirements_text = self._format_requirements(lab_requirements)
        
        prompt = f"""Информация о студенте:
- ФИО: {student_name}
- Группа: {group}
- Лабораторная работа №: {lab_number}

Требования к лабораторной работе:
{requirements_text}

Текст отчета студента:
---
{report_text}
---

Проанализируй отчет согласно требованиям и выстави оценку."""
        
        return prompt
    
    def _format_requirements(self, requirements: Dict) -> str:
        """Форматирование требований для промпта"""
        if not requirements:
            return "Стандартные требования к лабораторной работе:\n- Выполнение всех пунктов задания\n- Наличие кода программы\n- Результаты тестирования\n- Выводы"
        
        parts = []
        
        if requirements.get('description'):
            parts.append(f"Описание: {requirements['description']}")
        
        if requirements.get('tasks'):
            tasks = "\n".join([f"- {task}" for task in requirements['tasks']])
            parts.append(f"Задачи:\n{tasks}")
        
        if requirements.get('criteria'):
            criteria = "\n".join([f"- {c.get('name', '')}: {c.get('weight', 0)*100:.0f}%" 
                                 for c in requirements['criteria']])
            parts.append(f"Критерии оценки:\n{criteria}")
        
        if requirements.get('examples'):
            parts.append(f"Примеры выполнения: {requirements['examples']}")
        
        return "\n".join(parts) if parts else "Стандартные требования"
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Парсинг ответа от LLM"""
        result = {
            'score': 0,
            'max_score': 10,
            'comment': '',
            'criteria_scores': {}
        }
        
        lines = response_text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Извлечение оценки
            if line_lower.startswith('оценка:') or line_lower.startswith('оц:'):
                try:
                    score_str = line.split(':', 1)[1].strip()
                    result['score'] = float(''.join(filter(lambda x: x.isdigit() or x == '.', score_str)))
                except (ValueError, IndexError):
                    pass
            
            # Извлечение максимальной оценки
            elif line_lower.startswith('макс') or line_lower.startswith('max'):
                try:
                    max_str = line.split(':', 1)[1].strip()
                    result['max_score'] = float(''.join(filter(lambda x: x.isdigit() or x == '.', max_str)))
                except (ValueError, IndexError):
                    pass
            
            # Извлечение комментария
            elif line_lower.startswith('комментарий:') or line_lower.startswith('коммент:'):
                result['comment'] = line.split(':', 1)[1].strip()
            
            # Извлечение критериев
            elif line_lower.startswith('критерии:'):
                try:
                    json_str = line.split(':', 1)[1].strip()
                    result['criteria_scores'] = json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    pass
        
        # Если комментарий не найден в структурированном виде, берем остальной текст
        if not result['comment']:
            result['comment'] = response_text
        
        # Ограничение оценки диапазоном [0, max_score]
        result['score'] = max(0, min(result['score'], result['max_score']))
        
        return result
    
    def check_model_availability(self) -> bool:
        """Проверка доступности модели"""
        try:
            import ollama
            client = ollama.Client(host=self.host)
            models = client.list()
            
            model_names = [m.get('name', '') for m in models.get('models', [])]
            
            if any(self.model in name for name in model_names):
                return True
            
            logger.warning(f"Модель {self.model} не найдена. Доступные модели: {model_names}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки модели: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Получение списка доступных моделей"""
        try:
            import ollama
            client = ollama.Client(host=self.host)
            models = client.list()
            return [m.get('name', '') for m in models.get('models', [])]
        except Exception as e:
            logger.error(f"Ошибка получения списка моделей: {e}")
            return []
