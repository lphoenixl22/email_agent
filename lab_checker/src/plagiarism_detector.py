"""
Детектор плагиата для студенческих работ
Сравнение конфигураций MikroTik и текстов отчетов
"""
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PlagiarismDetector:
    """Детектор плагиата для лабораторных работ"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Порог схожести для обнаружения плагиата (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        self.submissions = []  # Хранилище всех работ
        
    def add_submission(self, student_id: str, report_text: str, 
                       mikrotik_config: Optional[Dict] = None):
        """
        Добавление работы студента для последующего сравнения
        
        Args:
            student_id: Уникальный идентификатор студента (email или ФИО)
            report_text: Текст отчета
            mikrotik_config: Извлеченная конфигурация MikroTik (если есть)
        """
        submission = {
            'student_id': student_id,
            'report_text': report_text,
            'mikrotik_config': mikrotik_config,
            'normalized_text': self._normalize_text(report_text),
            'config_hash': self._hash_config(mikrotik_config) if mikrotik_config else None
        }
        self.submissions.append(submission)
        logger.info(f"Добавлена работа студента {student_id} для проверки на плагиат")
        
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста для сравнения"""
        # Приведение к нижнему регистру
        text = text.lower()
        
        # Удаление лишних пробелов
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Удаление пунктуации (кроме важной для команд)
        text = re.sub(r'[^\w\s\./\-:]', '', text)
        
        # Удаление специфичных элементов (IP адреса, MAC адреса)
        text = re.sub(r'\d+\.\d+\.\d+\.\d+', 'IP_ADDR', text)
        text = re.sub(r'[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}', 'MAC_ADDR', text)
        
        return text
    
    def _hash_config(self, config: Dict) -> str:
        """Создание хэша конфигурации для быстрого сравнения"""
        if not config:
            return ""
        
        # Собираем ключевые элементы конфигурации
        elements = []
        
        # IP адреса (без конкретных значений)
        for ip in config.get('ip_addresses', []):
            # Нормализуем IP - оставляем только маску
            match = re.search(r'/(\d+)', ip)
            if match:
                elements.append(f"IP_MASK_{match.group(1)}")
        
        # Маршруты (только структура)
        for route in config.get('routes', []):
            elements.append("ROUTE")
        
        # Команды
        for cmd in config.get('commands_found', []):
            elements.append(cmd.upper())
        
        # Сортируем и создаем хэш
        elements.sort()
        return "|".join(elements)
    
    def check_plagiarism(self, student_id: str) -> Dict:
        """
        Проверка работы студента на плагиат
        
        Args:
            student_id: Идентификатор студента для проверки
            
        Returns:
            Словарь с результатами проверки
        """
        target_submission = None
        for sub in self.submissions:
            if sub['student_id'] == student_id:
                target_submission = sub
                break
        
        if not target_submission:
            return {
                'is_plagiarism': False,
                'matches': [],
                'similarity_score': 0.0
            }
        
        matches = []
        
        # Сравнение с другими работами
        for other_sub in self.submissions:
            if other_sub['student_id'] == student_id:
                continue
            
            # Вычисление схожести
            similarity = self._calculate_similarity(
                target_submission, 
                other_sub
            )
            
            if similarity >= self.similarity_threshold:
                matches.append({
                    'student_id': other_sub['student_id'],
                    'similarity': similarity,
                    'type': self._detect_match_type(target_submission, other_sub)
                })
        
        # Сортировка по убыванию схожести
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        is_plagiarism = len(matches) > 0 and matches[0]['similarity'] >= self.similarity_threshold
        
        return {
            'is_plagiarism': is_plagiarism,
            'matches': matches[:5],  # Топ 5 совпадений
            'similarity_score': matches[0]['similarity'] if matches else 0.0,
            'checked_against': len(self.submissions) - 1
        }
    
    def _calculate_similarity(self, sub1: Dict, sub2: Dict) -> float:
        """
        Вычисление коэффициента схожести между двумя работами
        
        Использует комбинированный подход:
        1. Сравнение нормализованного текста (Jaccard similarity)
        2. Сравнение конфигураций MikroTik
        """
        # Текстовая схожесть
        text_similarity = self._jaccard_similarity(
            set(sub1['normalized_text'].split()),
            set(sub2['normalized_text'].split())
        )
        
        # Схожесть конфигураций
        config_similarity = 0.0
        if sub1['config_hash'] and sub2['config_hash']:
            if sub1['config_hash'] == sub2['config_hash']:
                config_similarity = 1.0
            else:
                # Частичное совпадение конфигураций
                config_similarity = self._partial_config_match(
                    sub1.get('mikrotik_config', {}),
                    sub2.get('mikrotik_config', {})
                )
        
        # Комбинирование весов
        # Если есть конфигурация, она имеет больший вес
        if sub1['mikrotik_config'] or sub2['mikrotik_config']:
            return 0.3 * text_similarity + 0.7 * config_similarity
        else:
            return text_similarity
    
    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Коэффициент Жаккара для оценки схожести множеств"""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _partial_config_match(self, config1: Dict, config2: Dict) -> float:
        """Частичное совпадение конфигураций MikroTik"""
        if not config1 or not config2:
            return 0.0
        
        score = 0.0
        max_score = 0.0
        
        # Сравнение найденных команд
        cmds1 = set(config1.get('commands_found', []))
        cmds2 = set(config2.get('commands_found', []))
        if cmds1 or cmds2:
            max_score += 1.0
            if cmds1 and cmds2:
                score += self._jaccard_similarity(cmds1, cmds2)
        
        # Сравнение количества IP адресов
        ips1 = len(config1.get('ip_addresses', []))
        ips2 = len(config2.get('ip_addresses', []))
        if ips1 > 0 or ips2 > 0:
            max_score += 1.0
            if ips1 > 0 and ips2 > 0:
                # Схожесть по количеству (не по значениям)
                diff = abs(ips1 - ips2)
                score += max(0, 1.0 - diff * 0.2)
        
        # Сравнение маршрутов
        routes1 = len(config1.get('routes', []))
        routes2 = len(config2.get('routes', []))
        if routes1 > 0 or routes2 > 0:
            max_score += 1.0
            if routes1 > 0 and routes2 > 0:
                diff = abs(routes1 - routes2)
                score += max(0, 1.0 - diff * 0.25)
        
        # Наличие safe mode
        if 'has_safe_mode' in config1 or 'has_safe_mode' in config2:
            max_score += 0.5
            if config1.get('has_safe_mode') == config2.get('has_safe_mode'):
                score += 0.5
        
        return score / max_score if max_score > 0 else 0.0
    
    def _detect_match_type(self, sub1: Dict, sub2: Dict) -> str:
        """Определение типа совпадения"""
        if sub1['config_hash'] == sub2['config_hash'] and sub1['config_hash']:
            return "Идентичная конфигурация"
        
        text_sim = self._jaccard_similarity(
            set(sub1['normalized_text'].split()),
            set(sub2['normalized_text'].split())
        )
        
        if text_sim > 0.9:
            return "Почти идентичный текст"
        elif text_sim > 0.7:
            return "Высокая схожесть текста"
        else:
            return "Схожая структура конфигурации"
    
    def get_all_submissions_summary(self) -> List[Dict]:
        """Получение сводки по всем работам с проверкой на плагиат"""
        summary = []
        
        for sub in self.submissions:
            plagiarism_check = self.check_plagiarism(sub['student_id'])
            summary.append({
                'student_id': sub['student_id'],
                'has_plagiarism': plagiarism_check['is_plagiarism'],
                'similarity_score': plagiarism_check['similarity_score'],
                'matches_count': len(plagiarism_check['matches'])
            })
        
        return summary
    
    def clear(self):
        """Очистка хранилища работ"""
        self.submissions = []
        logger.info("Хранилище работ очищено")
