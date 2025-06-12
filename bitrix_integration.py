# -*- coding: utf-8 -*-
import requests
import json
import logging
from config import COMPANY_PHONES

async def send_to_bitrix(user_data, formatted_message, thread_id):
    """Отправляет расширенный запрос в Битрикс24 через webhook."""
    # TODO: Добавить реальный URL webhook и настройки
    # BITRIX_WEBHOOK_URL = "https://your-bitrix.bitrix24.ru/rest/webhook/..."
    
    payload = {
        "user_id": user_data.get("id"),
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name"),
        "language": user_data.get("language"),
        "formatted_message": formatted_message,
        "thread_id": thread_id,
        "source": "telegram_bot"
    }
    
    # Пока логируем расширенную информацию
    logging.info(f"Enhanced transfer to Bitrix24:")
    logging.info(f"User: {user_data.get('first_name')} (@{user_data.get('username')})")
    logging.info(f"Language: {user_data.get('language', 'ru')}")
    logging.info(f"Thread ID: {thread_id}")
    logging.info(f"Message length: {len(formatted_message)} characters")
    logging.info("─" * 50)
    logging.info(formatted_message)
    logging.info("─" * 50)
    
    # TODO: Раскомментировать когда будет webhook URL
    # try:
    #     response = requests.post(BITRIX_WEBHOOK_URL, json=payload, timeout=10)
    #     if response.status_code == 200:
    #         logging.info(f"Successfully sent enhanced data to Bitrix24: {response.json()}")
    #         return True
    #     else:
    #         logging.error(f"Bitrix24 error: {response.status_code} - {response.text}")
    #         return False
    # except Exception as e:
    #     logging.error(f"Error sending to Bitrix24: {e}")
    #     return False
    
    return True  # Пока возвращаем True для тестирования

def format_transfer_message():
    """Форматирует сообщение о передаче запроса менеджеру."""
    phones_text = "\n".join([f"📞 {phone}" for phone in COMPANY_PHONES])
    
    return (
        "Ваш запрос передан менеджеру. С вами свяжутся в ближайшее время.\n\n"
        f"Так же вы можете обратиться к нашим менеджерам по телефонам:\n{phones_text}"
    )