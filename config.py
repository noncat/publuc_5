# -*- coding: utf-8 -*-
import os
import logging

# Получение переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Пути к файлам
THREADS_DB_PATH = "data/threads.json"
LANGUAGES_DB_PATH = "data/languages.json"

# Контактная информация
COMPANY_PHONES = [
    "+998712073900",
    "+998712814356", 
    "+998712073400"
]

# Поддерживаемые языки
SUPPORTED_LANGUAGES = {
    'ru': 'Русский',
    'uz': 'O\'zbek',
    'en': 'English'
}

def validate_environment():
    """Проверяет наличие всех необходимых переменных окружения."""
    required_vars = {
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'OPENAI_API_KEY': OPENAI_API_KEY, 
        'ASSISTANT_ID': ASSISTANT_ID
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise SystemExit(f"Error: Missing environment variables: {', '.join(missing_vars)}")
    
    logging.info("All required environment variables are set")