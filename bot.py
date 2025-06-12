# -*- coding: utf-8 -*-
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Import our modules
from config import TELEGRAM_TOKEN, validate_environment, OPENAI_API_KEY, ASSISTANT_ID
from utils import log_user_action, load_threads, save_user_language, get_user_language
from openai_client import create_thread_for_user, get_run_status, get_assistant_response, submit_tool_outputs, cancel_run, format_conversation_for_manager
from bitrix_integration import send_to_bitrix, format_transfer_message

# OpenAI client import
from openai import OpenAI
import openai

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# OpenAI client initialization
client = OpenAI(api_key=OPENAI_API_KEY)

# Load saved thread_id on startup
user_threads = load_threads()

# Multilingual texts
TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте, {}!\n\n🤖 Я интерактивный помощник компании Web2Print\n\n✨ Что я умею:\n📋 Отвечаю на вопросы о наших услугах\n💰 Подсказываю цены и условия\n👨‍💼 Передаю сложные запросы менеджеру\n🌐 Работаю на 3 языках\n\n🎯 Выберите действие или просто напишите ваш вопрос!",
        
        'help': "❓ Как пользоваться ботом:\n\n💬 Просто напишите ваш вопрос обычным текстом\n📊 Спрашивайте о ценах, сроках, материалах\n📋 Уточняйте технические требования\n\n🔧 Доступные команды:\nℹ️ /info - информация о компании\n🌐 /lang - выбор языка\n🔄 /reset - начать разговор заново\n\n✅ Готов помочь с вашими задачами!",

        'company_info': "ℹ️ **Web2Print** - полиграфическая компания\n\n🏭 **Наши услуги:**\n• Оперативная полиграфия\n• Брендирование сувенирной продукции  \n• Фармацевтическая упаковка\n• Подарочная и ювелирная упаковка\n\n📞 **Контакты:**\n+998712073900\n+998712814356\n+998712073400\n\n📍 **Офис:** Яккасарайский р-н, 6 проезд, ул. Абдуллы Каххара 19/21\n\n🏗️ **Производство:** Чиланзарский р-н, ул. Дийдор, 103\n\n🕒 **Режим работы:** Пн-Пт 9:00-18:00\n\n🌐 **Сайт:** web2print.uz",

        'reset_success': '🔄 История беседы сброшена. Можем начать разговор заново!',
        'reset_empty': '💭 У вас пока нет активной беседы.',
        'choose_language': '🌐 Выберите язык / Tilni tanlang / Choose language:',
        'language_set': '✅ Язык изменен на русский',
        'contact_manager': "✅ Ваш запрос передан менеджеру. С вами свяжутся в ближайшее время.\n\n📞 Так же вы можете обратиться к нашим менеджерам:\n• +998712073900\n• +998712814356\n• +998712073400",
        'processing_error': '❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.',
        'timeout_error': '⏰ Извините, запрос выполняется слишком долго. Попробуйте позже.',
        'rate_limit_error': '🚫 Сервис временно перегружен. Попробуйте через несколько минут.',
        'api_error': '🔧 Проблема с сервисом ИИ. Попробуйте позже или обратитесь к оператору.',
        
        # Кнопки быстрых действий
        'quick_services': '📋 Наши услуги',
        'quick_language': '🌐 Сменить язык', 
        'quick_manager': '👨‍💼 Связаться с менеджером',
        'quick_info': 'ℹ️ О компании'
    },
    
    'uz': {
        'welcome': "👋 Salom, {}!\n\n🤖 Men Web2Print kompaniyasining interaktiv yordamchisiman\n\n✨ Men nima qila olaman:\n📋 Xizmatlarimiz haqida savollaringizga javob beraman\n💰 Narxlar va shartlarni aytaman\n👨‍💼 Murakkab so'rovlarni menejerga uzataman\n🌐 3 tilda ishlayman\n\n🎯 Harakat tanlang yoki savolingizni yozing!",

        'help': "❓ Botdan qanday foydalanish:\n\n💬 Savolingizni oddiy matn ko'rinishida yozing\n📊 Narxlar, muddatlar, materiallar haqida so'rang\n📋 Texnik talablarni aniqlang\n\n🔧 Mavjud buyruqlar:\nℹ️ /info - kompaniya haqida ma'lumot\n🌐 /lang - til tanlash\n🔄 /reset - suhbatni qaytadan boshlash\n\n✅ Vazifalaringizda yordam berishga tayyorman!",

        'company_info': "ℹ️ **Web2Print** - poligrafik kompaniya\n\n🏭 **Bizning xizmatlar:**\n• Tezkor poligrafiya\n• Sovg'a mahsulotlarini brendlash\n• Farmatsevtik qadoqlash\n• Sovg'a va zargarlik qadoqlash\n\n📞 **Kontaktlar:**\n+998712073900\n+998712814356\n+998712073400\n\n📍 **Ofis:** Yakkasaroy tumani, 6-o'tish, Abdulla Qahhor ko'chasi 19/21\n\n🏗️ **Ishlab chiqarish:** Chilonzor tumani, Diydor ko'chasi, 103\n\n🕒 **Ish vaqti:** Du-Ju 9:00-18:00\n\n🌐 **Sayt:** web2print.uz",

        'reset_success': '🔄 Suhbat tarixi tozalandi. Suhbatni qaytadan boshlashimiz mumkin!',
        'reset_empty': '💭 Sizda hali faol suhbat yo\'q.',
        'choose_language': '🌐 Выберите язык / Tilni tanlang / Choose language:',
        'language_set': '✅ Til o\'zbek (lotin) ga o\'zgartirildi',
        'contact_manager': "✅ So'rovingiz menejerga uzatildi. Siz bilan yaqin orada bog'lanishadi.\n\n📞 Shuningdek, menejerlarimiz bilan bog'lanishingiz mumkin:\n• +998712073900\n• +998712814356\n• +998712073400",
        'processing_error': '❌ So\'rovingizni qayta ishlashda xatolik yuz berdi. Iltimos, qaytadan urinib ko\'ring.',
        'timeout_error': '⏰ Kechirasiz, so\'rov juda uzoq davom etmoqda. Keyinroq urinib ko\'ring.',
        'rate_limit_error': '🚫 Xizmat vaqtincha yuklangan. Bir necha daqiqadan so\'ng urinib ko\'ring.',
        'api_error': '🔧 AI xizmatida muammo. Keyinroq urinib ko\'ring yoki operator bilan bog\'laning.',
        
        # Кнопки быстрых действий
        'quick_services': '📋 Bizning xizmatlar',
        'quick_language': '🌐 Tilni o\'zgartirish',
        'quick_manager': '👨‍💼 Menejr bilan bog\'lanish', 
        'quick_info': 'ℹ️ Kompaniya haqida'
    },
    
    'en': {
        'welcome': "👋 Hello, {}!\n\n🤖 I'm an interactive assistant of Web2Print company\n\n✨ What I can do:\n📋 Answer questions about our services\n💰 Provide prices and conditions\n👨‍💼 Transfer complex requests to managers\n🌐 Work in 3 languages\n\n🎯 Choose an action or just write your question!",

        'help': "❓ How to use the bot:\n\n💬 Simply write your question in plain text\n📊 Ask about prices, deadlines, materials\n📋 Clarify technical requirements\n\n🔧 Available commands:\nℹ️ /info - company information\n🌐 /lang - language selection\n🔄 /reset - start conversation over\n\n✅ Ready to help with your tasks!",

        'company_info': "ℹ️ **Web2Print** - printing company\n\n🏭 **Our services:**\n• Express printing\n• Promotional products branding\n• Pharmaceutical packaging\n• Gift and jewelry packaging\n\n📞 **Contacts:**\n+998712073900\n+998712814356\n+998712073400\n\n📍 **Office:** Yakkasaray district, 6th passage, Abdulla Qahhor street 19/21\n\n🏗️ **Production:** Chilanzar district, Diydor street, 103\n\n🕒 **Working hours:** Mon-Fri 9:00-18:00\n\n🌐 **Website:** web2print.uz",

        'reset_success': '🔄 Conversation history cleared. We can start the conversation over!',
        'reset_empty': '💭 You don\'t have an active conversation yet.',
        'choose_language': '🌐 Choose language / Tilni tanlang / Choose language:',
        'language_set': '✅ Language changed to English',
        'contact_manager': "✅ Your request has been transferred to a manager. They will contact you shortly.\n\n📞 You can also contact our managers:\n• +998712073900\n• +998712814356\n• +998712073400",
        'processing_error': '❌ An error occurred while processing your request. Please try again.',
        'timeout_error': '⏰ Sorry, the request is taking too long. Please try later.',
        'rate_limit_error': '🚫 Service is temporarily overloaded. Please try in a few minutes.',
        'api_error': '🔧 AI service problem. Please try later or contact an operator.',
        
        # Кнопки быстрых действий
        'quick_services': '📋 Our services',
        'quick_language': '🌐 Change language',
        'quick_manager': '👨‍💼 Contact manager',
        'quick_info': 'ℹ️ About company'
    }
}

def get_language_keyboard():
    """Creates language selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        ],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quick_actions_keyboard(user_lang):
    """Creates quick actions keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(TEXTS[user_lang]['quick_services'], callback_data="quick_services"),
            InlineKeyboardButton(TEXTS[user_lang]['quick_language'], callback_data="quick_language")
        ],
        [
            InlineKeyboardButton(TEXTS[user_lang]['quick_manager'], callback_data="quick_manager"),
            InlineKeyboardButton(TEXTS[user_lang]['quick_info'], callback_data="quick_info")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def safe_process_message(user_message, thread_id, user_lang):
    """Безопасно обрабатывает сообщение через OpenAI Assistant с проверкой активных run'ов."""
    try:
        # Проверяем активные run'ы в thread
        runs = client.beta.threads.runs.list(thread_id=thread_id, limit=5)
        
        # Отменяем все активные run'ы
        for run in runs.data:
            if run.status in ['queued', 'in_progress', 'requires_action']:
                logging.info(f"Cancelling active run {run.id} before new message")
                try:
                    cancel_run(thread_id, run.id)
                    # Даем время на отмену
                    time.sleep(1)
                except Exception as e:
                    logging.warning(f"Could not cancel run {run.id}: {e}")
        
        # Добавляем сообщение пользователя в thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        return run
        
    except openai.RateLimitError:
        return {"error": "rate_limit", "message": "Сервис временно перегружен. Попробуйте через несколько минут."}
    except openai.APIError as e:
        logging.error(f"OpenAI API error: {e}")
        return {"error": "api_error", "message": "Проблема с сервисом ИИ. Попробуйте позже или обратитесь к оператору."}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"error": "unknown", "message": "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends welcome message on /start command."""
    user = update.effective_user
    log_user_action(user.id, user.username, "START")
    
    # Get user language (default Russian)
    user_lang = get_user_language(user.id)
    
    # If language not set, show language selection
    if not user_lang:
        await update.message.reply_text(
            TEXTS['ru']['choose_language'],
            reply_markup=get_language_keyboard()
        )
        return
    
    welcome_text = TEXTS[user_lang]['welcome'].format(user.first_name)
    quick_actions_keyboard = get_quick_actions_keyboard(user_lang)
    
    await update.message.reply_text(welcome_text, reply_markup=quick_actions_keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends help message on /help command."""
    user = update.effective_user
    log_user_action(user.id, user.username, "HELP")
    
    user_lang = get_user_language(user.id) or 'ru'
    help_text = TEXTS[user_lang]['help']
    
    await update.message.reply_text(help_text)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends company information."""
    user = update.effective_user
    log_user_action(user.id, user.username, "INFO")
    
    user_lang = get_user_language(user.id) or 'ru'
    info_text = TEXTS[user_lang]['company_info']
    
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows language selection."""
    user = update.effective_user
    log_user_action(user.id, user.username, "LANG")
    
    await update.message.reply_text(
        TEXTS['ru']['choose_language'],
        reply_markup=get_language_keyboard()
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resets user conversation history."""
    user = update.effective_user
    log_user_action(user.id, user.username, "RESET")
    
    user_lang = get_user_language(user.id) or 'ru'
    user_id = update.effective_user.id
    
    if user_id in user_threads:
        del user_threads[user_id]
        from utils import save_threads
        save_threads(user_threads)
        await update.message.reply_text(TEXTS[user_lang]['reset_success'])
    else:
        await update.message.reply_text(TEXTS[user_lang]['reset_empty'])

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles language selection through inline buttons."""
    query = update.callback_query
    user = query.from_user
    
    await query.answer()
    
    # Extract language from callback_data
    lang_code = query.data.split('_')[1]  # lang_ru -> ru
    
    # Save selected language
    save_user_language(user.id, lang_code)
    log_user_action(user.id, user.username, f"LANG_SET", lang_code)
    
    # Send confirmation in selected language
    confirmation_text = TEXTS[lang_code]['language_set']
    await query.edit_message_text(confirmation_text)
    
    # Show welcome in selected language with quick actions
    welcome_text = TEXTS[lang_code]['welcome'].format(user.first_name)
    quick_actions_keyboard = get_quick_actions_keyboard(lang_code)
    await query.message.reply_text(welcome_text, reply_markup=quick_actions_keyboard)

async def process_assistant_request(query, message_text, user_lang):
    """Обрабатывает запрос к Assistant'у из inline кнопки с безопасной обработкой."""
    user_id = query.from_user.id
    user = query.from_user
    
    log_user_action(user.id, user.username, "QUICK_ACTION", message_text)
    
    # Create new thread if doesn't exist for user
    if user_id not in user_threads:
        thread_id = create_thread_for_user(user_id, user_threads)
    else:
        thread_id = user_threads[user_id]
    
    # Send typing indicator
    await query.message.chat.send_action(action="typing")
    
    # Process message through OpenAI using safe method
    result = await safe_process_message(message_text, thread_id, user_lang)
    
    # Check for errors
    if isinstance(result, dict) and "error" in result:
        error_type = result["error"]
        if error_type == "rate_limit":
            error_message = TEXTS[user_lang]['rate_limit_error']
        elif error_type == "api_error":
            error_message = TEXTS[user_lang]['api_error']
        else:
            error_message = TEXTS[user_lang]['processing_error']
        
        await query.message.reply_text(error_message)
        return
    
    # Wait for completion with timeout
    timeout_counter = 0
    max_timeout = 60
    
    while True:
        run_status = get_run_status(thread_id, result.id)
        
        if run_status.status == 'completed':
            break
        elif run_status.status == 'requires_action':
            # Assistant called transfer_to_manager function
            tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
            for tool_call in tool_calls:
                if tool_call.function.name == "transfer_to_manager":
                    # Создаем mock update для handle_transfer_to_manager
                    mock_update = type('MockUpdate', (), {
                        'effective_user': user,
                        'message': query.message
                    })()
                    await handle_transfer_to_manager(mock_update, tool_call, thread_id, result.id, user_lang)
                    return
        elif run_status.status in ['failed', 'cancelled', 'expired']:
            if run_status.status == 'cancelled':
                logging.info(f"Run {result.id} was cancelled as expected after transfer_to_manager")
            else:
                await query.message.reply_text(TEXTS[user_lang]['processing_error'])
            return
        
        timeout_counter += 1
        if timeout_counter > max_timeout:
            await query.message.reply_text(TEXTS[user_lang]['timeout_error'])
            return
        
        # Отправляем typing action каждые 4 секунды
        if timeout_counter % 4 == 0:
            await query.message.chat.send_action(action="typing")
            
        time.sleep(1)
    
    # Get assistant response
    assistant_response = get_assistant_response(thread_id)
    if assistant_response:
        await query.message.reply_text(assistant_response)

async def quick_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles quick action buttons."""
    query = update.callback_query
    user = query.from_user
    user_lang = get_user_language(user.id) or 'ru'
    
    await query.answer()
    
    action = query.data
    
    if action == "quick_services":
        # Отправляем запрос к Assistant'у о наших услугах
        services_questions = {
            'ru': "Расскажите о ваших услугах",
            'uz': "Xizmatlaringiz haqida gapiring",
            'en': "Tell me about your services"
        }
        
        # Обрабатываем как обычное сообщение пользователя
        await process_assistant_request(query, services_questions[user_lang], user_lang)
        
    elif action == "quick_language":
        # Показываем меню выбора языка
        await query.message.reply_text(
            TEXTS['ru']['choose_language'],
            reply_markup=get_language_keyboard()
        )
        
    elif action == "quick_manager":
        manager_requests = {
            'ru': "Хочу связаться с менеджером",
            'uz': "Menejr bilan bog'lanmoqchiman",
            'en': "I want to contact a manager"
        }
        
        await process_assistant_request(query, manager_requests[user_lang], user_lang)
        
    elif action == "quick_info":
        # Отправляем информацию о компании напрямую
        info_text = TEXTS[user_lang]['company_info']
        await query.message.reply_text(info_text, parse_mode='Markdown')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает полученный контакт пользователя."""
    user = update.effective_user
    contact = update.message.contact
    user_lang = get_user_language(user.id) or 'ru'
    
    # Проверяем, что контакт от самого пользователя
    if contact.user_id == user.id:
        phone_number = contact.phone_number
        log_user_action(user.id, user.username, "CONTACT_SHARED", phone_number)
        
        # Сохраняем номер телефона и отправляем обновление в Bitrix24
        user_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "language": user_lang,
            "phone": phone_number
        }
        
        # Отправляем обновление с номером телефона
        thread_id = user_threads.get(user.id)
        if thread_id:
            update_message = f"📞 ОБНОВЛЕНИЕ: Клиент поделился номером телефона: {phone_number}"
            await send_to_bitrix(user_data, update_message, thread_id)
        
        # Благодарим пользователя
        thanks_texts = {
            'ru': "✅ Спасибо! Ваш номер телефона передан менеджеру. С вами свяжутся в ближайшее время.",
            'uz': "✅ Rahmat! Telefon raqamingiz menejerga uzatildi. Siz bilan yaqin orada bog'lanishadi.",
            'en': "✅ Thank you! Your phone number has been sent to the manager. They will contact you soon."
        }
        
        message = thanks_texts.get(user_lang, thanks_texts['ru'])
        
    else:
        # Контакт от другого пользователя
        error_texts = {
            'ru': "❌ Пожалуйста, поделитесь своим собственным контактом.",
            'uz': "❌ Iltimos, o'zingizning kontaktingizni ulashing.",
            'en': "❌ Please share your own contact."
        }
        
        message = error_texts.get(user_lang, error_texts['ru'])
    
    # Убираем клавиатуру
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

async def handle_skip_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки 'Пропустить'."""
    user = update.effective_user
    user_lang = get_user_language(user.id) or 'ru'
    
    skip_texts = {
        'ru': "✅ Понятно. Менеджер свяжется с вами через Telegram.",
        'uz': "✅ Tushunarli. Menejr siz bilan Telegram orqali bog'lanadi.",
        'en': "✅ Understood. The manager will contact you via Telegram."
    }
    
    message = skip_texts.get(user_lang, skip_texts['ru'])
    
    log_user_action(user.id, user.username, "CONTACT_SKIPPED")
    
    # Убираем клавиатуру
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

async def handle_transfer_to_manager(update, tool_call, thread_id, run_id, user_lang):
    """Handles transfer request to manager with enhanced information."""
    user = update.effective_user
    log_user_action(user.id, user.username, "TRANSFER_TO_MANAGER")
    
    # Extract data from function call
    import json
    function_args = json.loads(tool_call.function.arguments)
    
    # Извлекаем все возможные параметры от Assistant'а
    summary = function_args.get("summary", "Client requested manager contact")
    technical_specs = function_args.get("technical_specs", None)
    recommendations = function_args.get("recommendations", None)
    
    # Prepare enhanced user data
    user_data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "language": user_lang,
        "phone": None  # Пока нет телефона
    }
    
    # Форматируем полную информацию для менеджера
    formatted_message = format_conversation_for_manager(
        thread_id=thread_id,
        user_data=user_data,
        summary=summary,
        technical_specs=technical_specs,
        recommendations=recommendations
    )
    
    # Send enhanced data to Bitrix24
    success = await send_to_bitrix(user_data, formatted_message, thread_id)
    
    # Cancel the current run to free the thread for future messages
    logging.info(f"Cancelling run {run_id} after transfer to manager")
    cancel_result = cancel_run(thread_id, run_id)
    
    if cancel_result:
        logging.info(f"Run {run_id} cancelled successfully")
    else:
        logging.error(f"Failed to cancel run {run_id}")
    
    # Создаем кнопку для запроса контакта
    contact_texts = {
        'ru': "📞 Поделиться номером телефона",
        'uz': "📞 Telefon raqamini ulashish", 
        'en': "📞 Share phone number"
    }
    
    skip_texts = {
        'ru': "⏭️ Пропустить",
        'uz': "⏭️ O'tkazib yuborish",
        'en': "⏭️ Skip"
    }
    
    contact_button_text = contact_texts.get(user_lang, contact_texts['ru'])
    skip_button_text = skip_texts.get(user_lang, skip_texts['ru'])
    
    keyboard = [
        [KeyboardButton(contact_button_text, request_contact=True)],
        [KeyboardButton(skip_button_text)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Сообщения о передаче с просьбой поделиться контактом
    contact_request_texts = {
        'ru': f"{TEXTS[user_lang]['contact_manager']}\n\n💡 Для более быстрой связи поделитесь номером телефона:",
        'uz': f"{TEXTS[user_lang]['contact_manager']}\n\n💡 Tezroq bog'lanish uchun telefon raqamingizni ulashing:",
        'en': f"{TEXTS[user_lang]['contact_manager']}\n\n💡 For faster contact, please share your phone number:"
    }
    
    message = contact_request_texts.get(user_lang, contact_request_texts['ru'])
    await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages from user and passes them to OpenAI Assistant."""
    user_id = update.effective_user.id
    user_message = update.message.text
    user = update.effective_user
    user_lang = get_user_language(user_id) or 'ru'
    
    log_user_action(user.id, user.username, "MESSAGE", user_message)
    
    # Create new thread if doesn't exist for user
    if user_id not in user_threads:
        thread_id = create_thread_for_user(user_id, user_threads)
    else:
        thread_id = user_threads[user_id]
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Process message through OpenAI using safe method
    result = await safe_process_message(user_message, thread_id, user_lang)
    
    # Check for errors
    if isinstance(result, dict) and "error" in result:
        error_type = result["error"]
        if error_type == "rate_limit":
            error_message = TEXTS[user_lang]['rate_limit_error']
        elif error_type == "api_error":
            error_message = TEXTS[user_lang]['api_error']
        else:
            error_message = TEXTS[user_lang]['processing_error']
        
        await update.message.reply_text(error_message)
        return
    
    # Wait for completion with timeout
    timeout_counter = 0
    max_timeout = 60
    
    while True:
        run_status = get_run_status(thread_id, result.id)
        
        if run_status.status == 'completed':
            break
        elif run_status.status == 'requires_action':
            # Assistant called transfer_to_manager function
            tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
            for tool_call in tool_calls:
                if tool_call.function.name == "transfer_to_manager":
                    await handle_transfer_to_manager(update, tool_call, thread_id, result.id, user_lang)
                    return  # Exit after transfer, run is cancelled
        elif run_status.status in ['failed', 'cancelled', 'expired']:
            if run_status.status == 'cancelled':
                # Run was cancelled after transfer_to_manager, this is expected
                logging.info(f"Run {result.id} was cancelled as expected after transfer_to_manager")
            else:
                await update.message.reply_text(TEXTS[user_lang]['processing_error'])
            return
        
        timeout_counter += 1
        if timeout_counter > max_timeout:
            await update.message.reply_text(TEXTS[user_lang]['timeout_error'])
            return
        
        # Отправляем typing action каждые 4 секунды
        if timeout_counter % 4 == 0:
            await update.message.chat.send_action(action="typing")
            
        time.sleep(1)
    
    # Get assistant response
    assistant_response = get_assistant_response(thread_id)
    if assistant_response:
        await update.message.reply_text(assistant_response)

async def set_bot_commands(application):
    """Sets bot command list."""
    commands = [
        ("start", "🚀 Start bot / Botni boshlash / Начать работу"),
        ("help", "❓ Get help / Yordam olish / Получить помощь"),
        ("info", "ℹ️ Company info / Kompaniya haqida / Информация о компании"),
        ("lang", "🌐 Language / Til tanlash / Выбор языка"),
        ("reset", "🔄 Reset history / Tarixni tozalash / Сбросить историю")
    ]
    await application.bot.set_my_commands(commands)

def main() -> None:
    """Starts the bot."""
    validate_environment()
    
    # Create application and add handlers
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(quick_actions_callback, pattern="^quick_"))
    
    # Обработчик контактов
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # Обработчик кнопки "Пропустить"
    skip_pattern = filters.Regex(r"^(⏭️ Пропустить|⏭️ O'tkazib yuborish|⏭️ Skip)$")
    application.add_handler(MessageHandler(skip_pattern, handle_skip_contact))
    
    # Обработчик обычных сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Set commands
    application.post_init = set_bot_commands
    
    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()