# -*- coding: utf-8 -*-
import openai
import logging
from openai import OpenAI
from config import OPENAI_API_KEY, ASSISTANT_ID
from utils import save_threads

# Инициализация OpenAI клиента
client = OpenAI(api_key=OPENAI_API_KEY)

def create_thread_for_user(user_id, user_threads):
    """Создает новый thread для пользователя."""
    thread = client.beta.threads.create()
    user_threads[user_id] = thread.id
    logging.info(f"Created new thread {thread.id} for user {user_id}")
    save_threads(user_threads)
    return thread.id

def get_run_status(thread_id, run_id):
    """Получает статус выполнения run."""
    return client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

def submit_tool_outputs(thread_id, run_id, tool_outputs):
    """Отправляет результаты выполнения функций."""
    try:
        return client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
    except Exception as e:
        logging.error(f"Error submitting tool outputs: {e}")
        return None

def cancel_run(thread_id, run_id):
    """Отменяет активный run."""
    try:
        result = client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
        logging.info(f"Run {run_id} cancelled successfully")
        return result
    except Exception as e:
        logging.error(f"Error cancelling run {run_id}: {e}")
        return None

def get_assistant_response(thread_id):
    """Получает последний ответ ассистента."""
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages.data:
        if message.role == "assistant":
            return message.content[0].text.value
    return None

def get_conversation_history(thread_id, limit=20):
    """Получает историю диалога из thread для передачи менеджеру."""
    try:
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=limit,
            order="asc"
        )
        
        conversation = []
        for message in reversed(messages.data):  # От старых к новым
            role = "👤 Клиент" if message.role == "user" else "🤖 Бот"
            content = message.content[0].text.value
            
            # Ограничиваем длину сообщения для читаемости
            if len(content) > 200:
                content = content[:200] + "..."
            
            conversation.append(f"{role}: {content}")
        
        return "\n".join(conversation)
        
    except Exception as e:
        logging.error(f"Error getting conversation history: {e}")
        return "Ошибка получения истории диалога"

def format_conversation_for_manager(thread_id, user_data, summary, technical_specs=None, recommendations=None):
    """Форматирует полную информацию для передачи менеджеру."""
    
    # Получаем историю диалога
    conversation_history = get_conversation_history(thread_id)
    
    # Форматируем сообщение для менеджера
    message_parts = []
    
    # Заголовок с информацией о клиенте
    message_parts.append("═══ КЛИЕНТ ═══")
    message_parts.append(f"👤 {user_data.get('first_name', 'Неизвестно')}")
    if user_data.get('username'):
        message_parts.append(f"📱 @{user_data['username']}")
    message_parts.append(f"🆔 Telegram ID: {user_data['id']}")
    message_parts.append(f"🌍 Язык: {user_data.get('language', 'ru')}")
    if user_data.get('phone'):
        message_parts.append(f"📞 Телефон: {user_data['phone']}")
    message_parts.append("")
    
    # История диалога
    message_parts.append("═══ ИСТОРИЯ ДИАЛОГА ═══")
    message_parts.append(conversation_history)
    message_parts.append("")
    
    # Краткое резюме
    message_parts.append("═══ КРАТКОЕ РЕЗЮМЕ ═══")
    message_parts.append(f"📋 {summary}")
    message_parts.append("")
    
    # Техническое задание (если есть)
    if technical_specs:
        message_parts.append("═══ ТЕХНИЧЕСКОЕ ЗАДАНИЕ ═══")
        message_parts.append(technical_specs)
        message_parts.append("")
    
    # Рекомендации менеджеру (если есть)
    if recommendations:
        message_parts.append("═══ РЕКОМЕНДАЦИИ МЕНЕДЖЕРУ ═══")
        message_parts.append("❓ Уточнить у клиента:")
        message_parts.append(recommendations)
        message_parts.append("")
    
    # Footer
    message_parts.append("═══════════════════════════")
    message_parts.append(f"🕐 Время передачи: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    return "\n".join(message_parts)

# Функция process_user_message больше не нужна - перенесена в bot.py как safe_process_message