# -*- coding: utf-8 -*-
import json
import logging
import time
import os
from config import THREADS_DB_PATH

# Путь к файлу с языками пользователей
LANGUAGES_DB_PATH = "data/languages.json"

def log_user_action(user_id, username, action, message_text=""):
    """Логирует действия пользователей."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} | User {user_id} (@{username}) | {action} | {message_text[:50]}"
    logging.info(log_entry)

def load_threads():
    """Загружает сохраненные треды из файла."""
    if os.path.exists(THREADS_DB_PATH) and os.path.getsize(THREADS_DB_PATH) > 0:
        try:
            with open(THREADS_DB_PATH, "r") as f:
                threads = json.load(f)
                # Конвертируем строковые ключи обратно в целые числа
                return {int(k): v for k, v in threads.items()}
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading threads data: {e}")
            return {}
    else:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(THREADS_DB_PATH), exist_ok=True)
        # Создаем пустой файл с пустым словарем
        with open(THREADS_DB_PATH, "w") as f:
            json.dump({}, f)
        return {}

def save_threads(threads_dict):
    """Сохраняет треды в файл."""
    try:
        # Преобразуем ключи из int в str для корректного JSON
        threads_str_keys = {str(k): v for k, v in threads_dict.items()}
        with open(THREADS_DB_PATH, "w") as f:
            json.dump(threads_str_keys, f)
        logging.info(f"Threads data saved to {THREADS_DB_PATH}")
    except IOError as e:
        logging.error(f"Error saving threads data: {e}")

def load_user_languages():
    """Загружает языки пользователей из файла."""
    if os.path.exists(LANGUAGES_DB_PATH) and os.path.getsize(LANGUAGES_DB_PATH) > 0:
        try:
            with open(LANGUAGES_DB_PATH, "r") as f:
                languages = json.load(f)
                # Конвертируем строковые ключи обратно в целые числа
                return {int(k): v for k, v in languages.items()}
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading languages data: {e}")
            return {}
    else:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(LANGUAGES_DB_PATH), exist_ok=True)
        # Создаем пустой файл с пустым словарем
        with open(LANGUAGES_DB_PATH, "w") as f:
            json.dump({}, f)
        return {}

def save_user_languages(languages_dict):
    """Сохраняет языки пользователей в файл."""
    try:
        # Преобразуем ключи из int в str для корректного JSON
        languages_str_keys = {str(k): v for k, v in languages_dict.items()}
        with open(LANGUAGES_DB_PATH, "w") as f:
            json.dump(languages_str_keys, f)
        logging.info(f"Languages data saved to {LANGUAGES_DB_PATH}")
    except IOError as e:
        logging.error(f"Error saving languages data: {e}")

# Глобальная переменная для хранения языков пользователей
_user_languages = load_user_languages()

def save_user_language(user_id, language_code):
    """Сохраняет выбранный язык пользователя."""
    global _user_languages
    _user_languages[user_id] = language_code
    save_user_languages(_user_languages)
    logging.info(f"Language set for user {user_id}: {language_code}")

def get_user_language(user_id):
    """Получает язык пользователя. Возвращает None, если язык не установлен."""
    global _user_languages
    return _user_languages.get(user_id)