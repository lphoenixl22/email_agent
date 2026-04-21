"""
Управление заданиями лабораторных работ
Загрузка из Git и локальных файлов
"""
import os
import json
import yaml
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LabManager:
    """Менеджер для управления заданиями лабораторных работ"""
    
    def __init__(self, labs_directory: str = "config/labs"):
        self.labs_directory = Path(labs_directory)
        self.labs_directory.mkdir(parents=True, exist_ok=True)
        self.labs_cache = {}
    
    def load_lab_requirements(self, lab_number: int) -> Optional[Dict]:
        """
        Загрузка требований к конкретной лабораторной работе
        
        Args:
            lab_number: Номер лабораторной работы
            
        Returns:
            Словарь с требованиями или None
        """
        # Проверка кэша
        if lab_number in self.labs_cache:
            return self.labs_cache[lab_number]
        
        # Поиск файла с требованиями
        req_file = self.labs_directory / f"lab_{lab_number}.yaml"
        
        if not req_file.exists():
            req_file = self.labs_directory / f"lab_{lab_number}.json"
        
        if not req_file.exists():
            # Пробуем найти по другим паттернам
            for pattern in [f"laboratory_{lab_number}.*", f"lr{lab_number}.*", f"лр{lab_number}.*"]:
                import glob
                matches = glob.glob(str(self.labs_directory / pattern))
                if matches:
                    req_file = Path(matches[0])
                    break
        
        if not req_file.exists():
            logger.warning(f"Требования для лабораторной {lab_number} не найдены")
            return self._get_default_requirements(lab_number)
        
        try:
            # Загрузка в зависимости от формата
            if req_file.suffix in ['.yaml', '.yml']:
                with open(req_file, 'r', encoding='utf-8') as f:
                    requirements = yaml.safe_load(f)
            elif req_file.suffix == '.json':
                with open(req_file, 'r', encoding='utf-8') as f:
                    requirements = json.load(f)
            else:
                # Текстовый файл с описанием
                with open(req_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    requirements = {
                        'description': content,
                        'tasks': [],
                        'criteria': []
                    }
            
            self.labs_cache[lab_number] = requirements
            logger.info(f"Загружены требования для лабораторной {lab_number}")
            return requirements
            
        except Exception as e:
            logger.error(f"Ошибка загрузки требований для лабораторной {lab_number}: {e}")
            return self._get_default_requirements(lab_number)
    
    def _get_default_requirements(self, lab_number: int) -> Dict:
        """Требования по умолчанию"""
        return {
            'lab_number': lab_number,
            'description': f'Лабораторная работа №{lab_number}',
            'tasks': [
                'Выполнить задание согласно варианту',
                'Предоставить исходный код программы',
                'Предоставить результаты тестирования',
                'Сделать выводы'
            ],
            'criteria': [
                {'name': 'Выполнение требований', 'weight': 0.4},
                {'name': 'Качество кода', 'weight': 0.3},
                {'name': 'Документация', 'weight': 0.2},
                {'name': 'Тестирование', 'weight': 0.1}
            ],
            'max_score': 10
        }
    
    def save_lab_requirements(self, lab_number: int, requirements: Dict):
        """Сохранение требований к лабораторной работе"""
        req_file = self.labs_directory / f"lab_{lab_number}.yaml"
        
        try:
            with open(req_file, 'w', encoding='utf-8') as f:
                yaml.dump(requirements, f, allow_unicode=True, default_flow_style=False)
            
            # Очистка кэша
            if lab_number in self.labs_cache:
                del self.labs_cache[lab_number]
            
            logger.info(f"Сохранены требования для лабораторной {lab_number}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения требований: {e}")
            raise
    
    def download_from_git(self, repo_url: str, branch: str = "main", 
                         target_path: Optional[str] = None) -> bool:
        """
        Загрузка заданий из Git репозитория
        
        Args:
            repo_url: URL Git репозитория
            branch: Ветка для клонирования
            target_path: Путь к папке с заданиями внутри репозитория
            
        Returns:
            True если загрузка успешна
        """
        try:
            from git import Repo
            import tempfile
            import shutil
            
            # Временная директория для клонирования
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Клонирование репозитория
                logger.info(f"Клонирование репозитория: {repo_url}")
                repo = Repo.clone_from(repo_url, temp_dir, branch=branch)
                
                # Определение целевой директории
                if target_path:
                    source_dir = Path(temp_dir) / target_path
                else:
                    source_dir = Path(temp_dir)
                
                # Копирование файлов с требованиями
                if source_dir.exists():
                    for file_path in source_dir.glob('*'):
                        if file_path.is_file() and file_path.suffix in ['.yaml', '.yml', '.json', '.md', '.txt']:
                            # Извлечение номера лабораторной из имени файла
                            lab_number = self._extract_lab_number_from_filename(file_path.name)
                            
                            if lab_number:
                                dest_file = self.labs_directory / f"lab_{lab_number}.yaml"
                                
                                # Конвертация в YAML если нужно
                                if file_path.suffix == '.json':
                                    with open(file_path, 'r', encoding='utf-8') as src:
                                        content = json.load(src)
                                    with open(dest_file, 'w', encoding='utf-8') as dst:
                                        yaml.dump(content, dst, allow_unicode=True)
                                else:
                                    shutil.copy2(file_path, dest_file)
                                
                                logger.info(f"Загружен файл для лабораторной {lab_number}")
                    
                    return True
                else:
                    logger.warning(f"Директория {target_path} не найдена в репозитории")
                    return False
                    
            finally:
                # Очистка временной директории
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except ImportError:
            logger.error("GitPython не установлен. Установите: pip install gitpython")
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки из Git: {e}")
            return False
    
    def _extract_lab_number_from_filename(self, filename: str) -> Optional[int]:
        """Извлечение номера лабораторной из имени файла"""
        import re
        
        patterns = [
            r'lab[_-]?(\d+)',
            r'laboratory[_-]?(\d+)',
            r'лр[_-]?(\d+)',
            r'лаб[_-]?(\d+)',
            r'(\d+)[_-]?lab',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def list_available_labs(self) -> List[int]:
        """Получение списка доступных лабораторных работ"""
        lab_numbers = set()
        
        # Сканирование директории
        for file_path in self.labs_directory.glob('lab_*.yaml'):
            try:
                num = int(file_path.stem.split('_')[1])
                lab_numbers.add(num)
            except (ValueError, IndexError):
                pass
        
        for file_path in self.labs_directory.glob('lab_*.json'):
            try:
                num = int(file_path.stem.split('_')[1])
                lab_numbers.add(num)
            except (ValueError, IndexError):
                pass
        
        return sorted(list(lab_numbers))
    
    def create_lab_template(self, lab_number: int, description: str = "",
                           tasks: List[str] = None, criteria: List[Dict] = None) -> Dict:
        """Создание шаблона требований для новой лабораторной"""
        
        if tasks is None:
            tasks = [
                "Изучить теоретический материал",
                "Выполнить задание согласно варианту",
                "Провести тестирование",
                "Оформить отчет"
            ]
        
        if criteria is None:
            criteria = [
                {'name': 'Полнота выполнения', 'weight': 0.4},
                {'name': 'Качество реализации', 'weight': 0.3},
                {'name': 'Оформление отчета', 'weight': 0.2},
                {'name': 'Защита работы', 'weight': 0.1}
            ]
        
        requirements = {
            'lab_number': lab_number,
            'description': description or f'Лабораторная работа №{lab_number}',
            'tasks': tasks,
            'criteria': criteria,
            'max_score': 10,
            'min_passing_score': 6
        }
        
        self.save_lab_requirements(lab_number, requirements)
        return requirements
