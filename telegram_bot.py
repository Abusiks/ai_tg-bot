import asyncio
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
    CallbackQueryHandler,          # <-- добавлено
)
from telegram.constants import ChatAction   # <-- добавлено

from config import BOT_TOKEN
from ollama_client import ask_llm, ask_llm_stream

# Хранилище истории диалогов
memory: Dict[int, List[str]] = {}

# Настройки автоматизации для пользователей
user_settings: Dict[int, dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Qwen 2.5 Coder подключён.\n\n"
        "📌 **Новые возможности:**\n"
        "• Упомяните меня @username в любом чате\n"
        "• Я отвечаю с эффектом печатания\n"
        "• Команда /settings для настройки\n"
        "• Команда /clear для очистки истории"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    memory[user_id] = []
    await update.message.reply_text("🧹 Контекст очищен.")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    keyboard = [
        [
            InlineKeyboardButton("📩 Отвечать на все чаты", callback_data="auto_all"),
            InlineKeyboardButton("👤 Только новые чаты", callback_data="auto_new"),
        ],
        [
            InlineKeyboardButton("🚫 Исключить контакты", callback_data="auto_no_contacts"),
            InlineKeyboardButton("⏹ Отключить автоответ", callback_data="auto_off"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ **Настройка автоматизации чатов**\n\n"
        "Выберите режим работы бота:",
        reply_markup=reply_markup,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data == "auto_all":
        user_settings[user_id] = {"mode": "all"}
        await query.edit_message_text("✅ Режим: отвечать на все чаты")
    elif data == "auto_new":
        user_settings[user_id] = {"mode": "new"}
        await query.edit_message_text("✅ Режим: только новые чаты")
    elif data == "auto_no_contacts":
        user_settings[user_id] = {"mode": "no_contacts"}
        await query.edit_message_text("✅ Режим: все чаты, кроме контактов")
    elif data == "auto_off":
        user_settings[user_id] = {"mode": "off"}
        await query.edit_message_text("⏹ Автоответ отключён")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text

    # --- Автоматизация чатов: проверяем настройки пользователя ---
    if user_id in user_settings:
        mode = user_settings[user_id].get("mode", "off")
        if mode == "off":
            return  # игнорируем, если автоответ выключен

    # --- Инициализация истории ---
    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(f"User: {text}")
    history = "\n".join(memory[user_id][-20:])

    prompt = f"""
Ты полезный AI ассистент.

История:

{history}

Ответь на последнее сообщение пользователя.
"""

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # Потоковая генерация
        full_answer = ""
        async for chunk in ask_llm_stream(prompt):
            full_answer += chunk

        memory[user_id].append(f"Assistant: {full_answer}")

        if len(full_answer) > 4000:
            for i in range(0, len(full_answer), 4000):
                await update.message.reply_text(full_answer[i:i+4000])
        else:
            await update.message.reply_text(full_answer)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # опционально – можно перегенерировать ответ
    pass


def create_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.UpdateType.EDITED_MESSAGE,
            handle_edited_message
        )
    )

    return app