import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set!")
    exit(1)

# Data storage
user_reminders = {}
user_todos = {}

# Conversation states
REMINDER_MESSAGE, REMINDER_TIME = range(2)
TODO_MESSAGE = range(1)

def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None

# ========== COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 Welcome to TaskMaster Bot!\n\n"
        "I can help you with:\n"
        "✅ Reminders\n"
        "✅ To-do lists\n"
        "✅ Productivity\n\n"
        "Type /help to see all commands"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/ping - Check if bot is alive\n"
        "/remind - Set a reminder\n"
        "/reminders - View all reminders\n"
        "/todo - Add a todo\n"
        "/mytodos - View all todos\n"
        "/done - Mark todo as done\n"
        "/delete - Delete a todo"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot is running!")

# ========== REMINDERS (Using ConversationHandler) ==========

async def remind_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start reminder setup"""
    await update.message.reply_text(
        "📝 Send me your reminder message:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_reminder")]
        ])
    )
    return REMINDER_MESSAGE

async def remind_get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get reminder message"""
    context.user_data['reminder_message'] = update.message.text
    await update.message.reply_text(
        "⏰ Send the time (YYYY-MM-DD HH:MM)\nExample: 2026-07-05 15:30",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_reminder")]
        ])
    )
    return REMINDER_TIME

async def remind_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get reminder time and save"""
    user_id = update.effective_user.id
    time_str = update.message.text
    reminder_time = parse_time(time_str)
    
    if not reminder_time:
        await update.message.reply_text("❌ Invalid format! Use YYYY-MM-DD HH:MM")
        return REMINDER_TIME
    
    if reminder_time < datetime.now():
        await update.message.reply_text("❌ Time must be in the future!")
        return REMINDER_TIME
    
    if user_id not in user_reminders:
        user_reminders[user_id] = []
    
    reminder_id = len(user_reminders[user_id]) + 1
    reminder = {
        'id': reminder_id,
        'message': context.user_data.get('reminder_message', 'No message'),
        'time': reminder_time
    }
    user_reminders[user_id].append(reminder)
    
    await update.message.reply_text(
        f"✅ Reminder set!\n\n"
        f"📝 {reminder['message']}\n"
        f"⏰ {format_time(reminder_time)}\n"
        f"🆔 ID: {reminder_id}"
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel reminder setup"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Reminder cancelled")
    context.user_data.clear()
    return ConversationHandler.END

async def view_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all reminders"""
    user_id = update.effective_user.id
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 You have no reminders set.")
        return
    
    text = "📋 Your Reminders:\n\n"
    for r in user_reminders[user_id]:
        text += f"🆔 {r['id']}: {r['message']}\n⏰ {format_time(r['time'])}\n\n"
    
    await update.message.reply_text(text)

# ========== TODOS (Using ConversationHandler) ==========

async def todo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start todo setup"""
    await update.message.reply_text(
        "📝 Send me your todo item:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_todo")]
        ])
    )
    return TODO_MESSAGE

async def todo_get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get todo message and save"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_todos:
        user_todos[user_id] = []
    
    todo_id = len(user_todos[user_id]) + 1
    user_todos[user_id].append({
        'id': todo_id,
        'text': text,
        'done': False
    })
    
    await update.message.reply_text(f"✅ Todo added! (ID: {todo_id})")
    return ConversationHandler.END

async def cancel_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel todo setup"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Todo cancelled")
    return ConversationHandler.END

async def view_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all todos"""
    user_id = update.effective_user.id
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 Your todo list is empty!")
        return
    
    text = "📋 Your Todos:\n\n"
    for t in user_todos[user_id]:
        status = "✅" if t['done'] else "⬜"
        text += f"{status} {t['id']}: {t['text']}\n"
    
    await update.message.reply_text(text)

async def done_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark todo as done"""
    user_id = update.effective_user.id
    if user_id not in user_todos:
        await update.message.reply_text("📭 No todos")
        return
    
    pending = [t for t in user_todos[user_id] if not t['done']]
    if not pending:
        await update.message.reply_text("🎉 All your todos are done!")
        return
    
    keyboard = []
    for t in pending:
        keyboard.append([InlineKeyboardButton(f"{t['id']}: {t['text']}", callback_data=f"done_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_done")])
    
    await update.message.reply_text(
        "✅ Select a todo to mark as done:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete todo"""
    user_id = update.effective_user.id
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 No todos")
        return
    
    keyboard = []
    for t in user_todos[user_id]:
        keyboard.append([InlineKeyboardButton(f"{t['id']}: {t['text']}", callback_data=f"delete_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")])
    
    await update.message.reply_text(
        "🗑️ Select a todo to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== CALLBACKS ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Handle cancellations
    if data == "cancel_done" or data == "cancel_delete":
        await query.edit_message_text("❌ Cancelled")
        return
    
    # Handle done
    if data.startswith("done_"):
        todo_id = int(data.split("_")[1])
        for t in user_todos.get(user_id, []):
            if t['id'] == todo_id:
                t['done'] = True
                await query.edit_message_text(f"✅ Done: {t['text']}")
                break
        return
    
    # Handle delete
    if data.startswith("delete_"):
        todo_id = int(data.split("_")[1])
        if user_id in user_todos:
            user_todos[user_id] = [t for t in user_todos[user_id] if t['id'] != todo_id]
            await query.edit_message_text("🗑️ Deleted")
        return

# ========== ERROR ==========

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ Error occurred. Please try again.")

# ========== MAIN ==========

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ===== REMINDER CONVERSATION =====
    remind_conv = ConversationHandler(
        entry_points=[CommandHandler('remind', remind_start)],
        states={
            REMINDER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_get_message)],
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_get_time)],
        },
        fallbacks=[CommandHandler('cancel', cancel_reminder), CallbackQueryHandler(cancel_reminder, pattern='cancel_reminder')]
    )
    
    # ===== TODO CONVERSATION =====
    todo_conv = ConversationHandler(
        entry_points=[CommandHandler('todo', todo_start)],
        states={
            TODO_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, todo_get_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel_todo), CallbackQueryHandler(cancel_todo, pattern='cancel_todo')]
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(remind_conv)  # Full reminder conversation
    app.add_handler(todo_conv)    # Full todo conversation
    app.add_handler(CommandHandler("reminders", view_reminders))
    app.add_handler(CommandHandler("mytodos", view_todos))
    app.add_handler(CommandHandler("done", done_todo))
    app.add_handler(CommandHandler("delete", delete_todo))
    
    # Callback handler for all buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
