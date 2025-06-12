#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обработки диалогов из Битрикс24 и создания Q&A пар для базы знаний
"""

import pandas as pd
import json
import re
import glob
import os
from datetime import datetime
from typing import List, Dict, Tuple
import sys
import argparse

class DialogueProcessor:
    def __init__(self):
        self.qa_pairs = []
    
    def read_excel_file(self, file_path: str) -> pd.DataFrame:
        """Читает Excel файл с диалогами или HTML файл"""
        try:
            # Читаем первые байты файла для определения типа
            with open(file_path, 'rb') as f:
                first_bytes = f.read(10)
            
            # Проверяем, это HTML файл
            if first_bytes.startswith(b'\xef\xbb\xbf<html') or first_bytes.startswith(b'<html') or first_bytes.startswith(b'<!DOCTYPE'):
                # Это HTML файл - читаем как HTML таблицу
                print("🔍 Обнаружен HTML файл, читаем как таблицу...")
                tables = pd.read_html(file_path, encoding='utf-8')
                
                if not tables:
                    raise ValueError("HTML таблицы не найдены")
                
                # Берем первую таблицу (обычно самую большую)
                df = tables[0]
                
            else:
                # Настоящий Excel файл
                print("🔍 Обнаружен Excel файл...")
                if file_path.lower().endswith('.xls'):
                    df = pd.read_excel(file_path, engine='xlrd')
                else:
                    df = pd.read_excel(file_path, engine='openpyxl')
            
            print(f"✅ Файл загружен: {len(df)} строк")
            print(f"📋 Колонки: {list(df.columns)}")
            
            # Показываем первые несколько строк для отладки
            print(f"🔍 Первые строки данных:")
            print(df.head(2))
            
            return df
            
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            print(f"💡 Проверьте формат файла")
            sys.exit(1)
    
    def clean_message(self, message: str) -> str:
        """Очищает сообщение от лишних символов"""
        if not message or pd.isna(message):
            return ""
        
        message = str(message)
        # Убираем \\n
        message = message.replace('\\n', '\n')
        # Убираем лишние пробелы
        message = re.sub(r'\s+', ' ', message).strip()
        # Убираем URL-ы
        message = re.sub(r'https?://\S+', '[ССЫЛКА]', message)
        
        return message
    
    def parse_dialogue(self, dialogue_text: str, client_name: str) -> List[Dict]:
        """Парсит диалог на отдельные сообщения"""
        if not dialogue_text or pd.isna(dialogue_text):
            return []
        
        dialogue_text = self.clean_message(dialogue_text)
        messages = []
        
        # Список известных операторов
        operators = ['Sitora', 'Yulia', 'Yuliya', 'Sofiya', 'Anton', 'Liliya']
        all_speakers = [client_name] + operators
        
        # Находим все позиции где встречается "Имя:"
        positions = []
        for speaker in all_speakers:
            speaker_pattern = f"{speaker}:"
            start = 0
            while True:
                pos = dialogue_text.find(speaker_pattern, start)
                if pos == -1:
                    break
                positions.append((pos, speaker))
                start = pos + 1
        
        # Сортируем по позиции
        positions.sort()
        
        # Извлекаем сообщения
        for i, (pos, speaker) in enumerate(positions):
            # Находим начало текста (после "Имя:")
            text_start = pos + len(speaker) + 1
            
            # Находим конец текста (до следующего "Имя:" или конец строки)
            if i + 1 < len(positions):
                text_end = positions[i + 1][0]
            else:
                text_end = len(dialogue_text)
            
            text = dialogue_text[text_start:text_end].strip()
            
            if text and len(text) > 2:
                # Убираем возможные остатки других имен в конце
                for other_speaker in all_speakers:
                    if text.endswith(f" {other_speaker}"):
                        text = text[:-len(other_speaker)-1].strip()
                
                is_client = speaker == client_name
                
                messages.append({
                    'speaker': speaker,
                    'text': text,
                    'is_client': is_client
                })
        
        return messages
    
    def is_good_qa_pair(self, question: str, answer: str) -> bool:
        """Проверяет качество Q&A пары"""
        # Минимальная длина
        if len(question) < 10 or len(answer) < 5:
            return False
        
        # Проверяем, что это действительно вопрос
        question_indicators = ['?', 'как', 'что', 'где', 'когда', 'сколько', 'можно', 'есть']
        has_question_indicator = any(indicator in question.lower() for indicator in question_indicators)
        
        # Проверяем, что ответ информативный
        bad_answers = ['да', 'нет', 'хорошо', 'ок', 'понятно', 'спасибо']
        is_bad_answer = answer.lower().strip() in bad_answers
        
        return has_question_indicator and not is_bad_answer
    
    def extract_full_dialogues(self, df: pd.DataFrame) -> List[Dict]:
        """Извлекает ПОЛНЫЕ диалоги, а не отдельные Q&A пары"""
        full_dialogues = []
        
        print(f"\n🔍 Анализируем {len(df)} диалогов...")
        
        for idx, row in df.iterrows():
            client_name = str(row.get('Клиент', ''))
            dialogue_text = row.get('Диалог (Demo)', '')
            
            if not dialogue_text:
                continue
            
            messages = self.parse_dialogue(dialogue_text, client_name)
            
            if len(messages) == 0:
                continue  # Пропускаем только пустые диалоги
                
            # Сохраняем ВЕСЬ диалог целиком
            full_dialogues.append({
                'dialogue_id': row.get('№', idx),
                'client': client_name,
                'operator': messages[0]['speaker'] if not messages[0]['is_client'] else (messages[1]['speaker'] if len(messages) > 1 else 'Unknown'),
                'messages': messages,
                'message_count': len(messages)
            })
        
        return full_dialogues
    
    def save_to_json(self, full_dialogues: List[Dict], output_file: str):
        """Сохраняет полные диалоги в JSON"""
        output_data = {
            'meta': {
                'total_dialogues': len(full_dialogues),
                'total_messages': sum(d['message_count'] for d in full_dialogues),
                'generated_by': 'DialogueProcessor v2.0'
            },
            'dialogues': full_dialogues
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON файл сохранен в {output_file}")
    
    def save_to_txt(self, full_dialogues: List[Dict], output_file: str):
        """Сохраняет ПОЛНЫЕ диалоги в TXT для загрузки в Vector Store"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("База знаний из реальных диалогов клиентов Web2Print\n\n")
            f.write("КЛЮЧЕВЫЕ СЛОВА: полиграфия, печать, сроки, цены, материалы, дизайн, клиенты, заказы\n\n")
            
            for i, dialogue in enumerate(full_dialogues, 1):
                f.write(f"ДИАЛОГ {i} - ID {dialogue['dialogue_id']}\n")
                f.write(f"Клиент: {dialogue['client']}\n")
                f.write(f"Оператор: {dialogue['operator']}\n")
                f.write(f"Количество сообщений: {dialogue['message_count']}\n\n")
                
                f.write("ПОЛНЫЙ ДИАЛОГ:\n")
                
                # Записываем ВСЕ сообщения по порядку
                for msg in dialogue['messages']:
                    role = "Клиент" if msg['is_client'] else "Оператор"
                    f.write(f"{role}: {msg['text']}\n")
                
                f.write("\n")
                
                # Анализируем ТОЛЬКО общие бизнес-темы диалога (БЕЗ продукции)
                topics = set()
                dialogue_text = " ".join([msg['text'].lower() for msg in dialogue['messages']])
                
                if any(word in dialogue_text for word in ['цена', 'стоимость', 'сколько', 'стоит', 'рубл', 'сум']):
                    topics.add('Ценообразование')
                if any(word in dialogue_text for word in ['срок', 'время', 'когда', 'готов', 'день', 'час']):
                    topics.add('Сроки изготовления')
                if any(word in dialogue_text for word in ['размер', 'формат', 'сантиметр', 'мм', 'см']):
                    topics.add('Технические характеристики')
                if any(word in dialogue_text for word in ['дизайн', 'макет', 'файл', 'картинк', 'изображен']):
                    topics.add('Дизайн и макеты')
                if any(word in dialogue_text for word in ['доставк', 'самовывоз', 'привез', 'курьер']):
                    topics.add('Доставка')
                if any(word in dialogue_text for word in ['оплат', 'плат', 'счет', 'деньг']):
                    topics.add('Оплата')
                if any(word in dialogue_text for word in ['материал', 'бумаг', 'ткан', 'качеств']):
                    topics.add('Материалы')
                if any(word in dialogue_text for word in ['заказ', 'оформ', 'как получ']):
                    topics.add('Процесс заказа')
                
                f.write("КЛЮЧЕВЫЕ ТЕМЫ: ")
                if topics:
                    f.write(f"{', '.join(sorted(topics))}\n\n")
                else:
                    f.write("Общие вопросы\n\n")
                
                f.write("---\n\n")
            
            f.write("ИНФОРМАЦИЯ О БАЗЕ ЗНАНИЙ\n")
            f.write(f"Всего диалогов: {len(full_dialogues)}\n")
            f.write(f"Всего сообщений: {sum(d['message_count'] for d in full_dialogues)}\n")
            f.write(f"Источник: Реальные диалоги клиентов из Битрикс24\n")
            f.write(f"Компания: Web2Print - полиграфические услуги\n")
            f.write(f"Обработано автоматически из выгрузки диалогов\n")
        
        print(f"✅ TXT файл сохранен в {output_file}")
    
    def print_statistics(self, qa_pairs: List[Dict]):
        """Выводит статистику по извлеченным парам"""
        print(f"\n📊 СТАТИСТИКА:")
        print(f"Всего Q&A пар: {len(qa_pairs)}")
        
        # Показываем несколько примеров
        print(f"\n💎 Примеры Q&A пар:")
        for i, qa in enumerate(qa_pairs[:3]):
            print(f"\n{i+1}. Клиент: {qa['client']}")
            print(f"   ❓ {qa['question']}")
            print(f"   ✅ {qa['answer']}")
    
    def process_file(self, input_file: str):
        """Основная функция обработки файла"""
        # Читаем файл
        df = self.read_excel_file(input_file)
        
        # Извлекаем ПОЛНЫЕ диалоги
        full_dialogues = self.extract_full_dialogues(df)
        
        return full_dialogues

def find_excel_files(directory='.'):
    """Находит все Excel файлы в директории"""
    patterns = ['*.xls', '*.xlsx']
    files = []
    
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(directory, pattern)))
    
    return files

def create_output_directory():
    """Создает папку для результатов с датой и временем"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"dialogue_processing_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def main():
    parser = argparse.ArgumentParser(description='Обработка диалогов в Q&A пары')
    parser.add_argument('--file', help='Конкретный файл для обработки')
    parser.add_argument('--dir', default='.', help='Директория для поиска Excel файлов (по умолчанию текущая)')
    parser.add_argument('--output-dir', help='Директория для сохранения результатов (создается автоматически если не указана)')
    
    args = parser.parse_args()
    
    processor = DialogueProcessor()
    
    # Создаем директорию для результатов
    if args.output_dir:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = create_output_directory()
    
    print(f"📁 Результаты будут сохранены в: {output_dir}")
    
    # Определяем файлы для обработки
    if args.file:
        # Обрабатываем конкретный файл
        if not os.path.exists(args.file):
            print(f"❌ Файл не найден: {args.file}")
            sys.exit(1)
        files_to_process = [args.file]
    else:
        # Ищем все Excel файлы в директории
        files_to_process = find_excel_files(args.dir)
        
        if not files_to_process:
            print(f"❌ Excel файлы не найдены в {args.dir}")
            print("💡 Убедитесь что файлы имеют расширение .xls или .xlsx")
            sys.exit(1)
        
        print(f"📄 Найдено Excel файлов: {len(files_to_process)}")
        for f in files_to_process:
            print(f"   📄 {f}")
        print()
    
    all_dialogues = []
    processing_info = {
        'timestamp': datetime.now().isoformat(),
        'files_processed': [],
        'total_dialogues': 0,
        'total_messages': 0,
        'output_directory': output_dir
    }
    
    # Обрабатываем каждый файл
    for file_path in files_to_process:
        print(f"🔄 Обрабатываем: {os.path.basename(file_path)}")
        
        try:
            dialogues = processor.process_file(file_path)
            all_dialogues.extend(dialogues)
            
            total_messages = sum(d['message_count'] for d in dialogues)
            
            file_info = {
                'filename': os.path.basename(file_path),
                'full_path': file_path,
                'dialogues_extracted': len(dialogues),
                'messages_extracted': total_messages,
                'status': 'success'
            }
            processing_info['files_processed'].append(file_info)
            
            print(f"✅ Извлечено {len(dialogues)} диалогов ({total_messages} сообщений) из {os.path.basename(file_path)}")
        except Exception as e:
            print(f"❌ Ошибка обработки {file_path}: {e}")
            
            file_info = {
                'filename': os.path.basename(file_path),
                'full_path': file_path,
                'dialogues_extracted': 0,
                'messages_extracted': 0,
                'status': 'error',
                'error': str(e)
            }
            processing_info['files_processed'].append(file_info)
            continue
    
    if not all_dialogues:
        print("❌ Не удалось извлечь диалоги ни из одного файла")
        sys.exit(1)
    
    processing_info['total_dialogues'] = len(all_dialogues)
    processing_info['total_messages'] = sum(d['message_count'] for d in all_dialogues)
    
    # Определяем базовые имена файлов
    if len(files_to_process) == 1:
        # Один файл - используем его имя
        base_name = os.path.splitext(os.path.basename(files_to_process[0]))[0]
    else:
        # Несколько файлов - общее имя
        base_name = "combined_dialogues"
    
    # Пути для выходных файлов в созданной директории
    json_output = os.path.join(output_dir, f"{base_name}_full_dialogues.json")
    txt_output = os.path.join(output_dir, f"{base_name}_knowledge_base.txt")
    info_output = os.path.join(output_dir, "processing_info.json")
    
    # Сохраняем результаты
    print(f"\n📊 ИТОГО извлечено диалогов: {len(all_dialogues)}")
    print(f"📊 ИТОГО сообщений: {sum(d['message_count'] for d in all_dialogues)}")
    
    processor.save_to_json(all_dialogues, json_output)
    processor.save_to_txt(all_dialogues, txt_output)
    
    # Сохраняем информацию о процессе обработки
    with open(info_output, 'w', encoding='utf-8') as f:
        json.dump(processing_info, f, ensure_ascii=False, indent=2)
    
    print(f"ℹ️ Информация о процессе сохранена в {info_output}")
    print(f"\n🎉 Готово! Все файлы сохранены в папке: {output_dir}")
    print(f"📋 Основной файл для Vector Store: {txt_output}")

if __name__ == "__main__":
    main()