import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

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

# ========== REMINDERS ==========

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'reminder_message'
    await update.message.reply_text(
        "📝 Send me your reminder message:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
    )

async def handle_reminder_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') == 'reminder_message':
        context.user_data['msg'] = update.message.text
        context.user_data['step'] = 'reminder_time'
        await update.message.reply_text(
            "⏰ Send the time (YYYY-MM-DD HH:MM)\nExample: 2026-07-05 15:30"
        )

async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') == 'reminder_time':
        user_id = update.effective_user.id
        time_str = update.message.text
        reminder_time = parse_time(time_str)
        
        if not reminder_time:
            await update.message.reply_text("❌ Invalid format! Use YYYY-MM-DD HH:MM")
            return
        
        if reminder_time < datetime.now():
            await update.message.reply_text("❌ Time must be in the future!")
            return
        
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder_id = len(user_reminders[user_id]) + 1
        reminder = {
            'id': reminder_id,
            'message': context.user_data.get('msg', 'No message'),
            'time': reminder_time
        }
        user_reminders[user_id].append(reminder)
        
        context.user_data['step'] = None
        context.user_data['msg'] = None
        
        await update.message.reply_text(
            f"✅ Reminder set!\n\n📝 {reminder['message']}\n⏰ {format_time(reminder_time)}\n🆔 ID: {reminder_id}"
        )

async def view_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 No reminders")
        return
    
    text = "📋 Your Reminders:\n\n"
    for r in user_reminders[user_id]:
        text += f"🆔 {r['id']}: {r['message']}\n⏰ {format_time(r['time'])}\n\n"
    
    await update.message.reply_text(text)

# ========== TODOS ==========

async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'todo_message'
    await update.message.reply_text(
        "📝 Send me your todo item:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
    )

async def handle_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') == 'todo_message':
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
        
        context.user_data['step'] = None
        await update.message.reply_text(f"✅ Todo added! (ID: {todo_id})")

async def view_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 No todos")
        return
    
    text = "📋 Your Todos:\n\n"
    for t in user_todos[user_id]:
        status = "✅" if t['done'] else "⬜"
        text += f"{status} {t['id']}: {t['text']}\n"
    
    await update.message.reply_text(text)

async def done_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_todos:
        await update.message.reply_text("📭 No todos")
        return
    
    pending = [t for t in user_todos[user_id] if not t['done']]
    if not pending:
        await update.message.reply_text("🎉 All done!")
        return
    
    keyboard = []
    for t in pending:
        keyboard.append([InlineKeyboardButton(t['text'], callback_data=f"done_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        "✅ Select todo to mark as done:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 No todos")
        return
    
    keyboard = []
    for t in user_todos[user_id]:
        keyboard.append([InlineKeyboardButton(t['text'], callback_data=f"delete_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        "🗑️ Select todo to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== CALLBACKS ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "cancel":
        context.user_data['step'] = None
        context.user_data['msg'] = None
        await query.edit_message_text("❌ Cancelled")
        return
    
    if data.startswith("done_"):
        todo_id = int(data.split("_")[1])
        for t in user_todos.get(user_id, []):
            if t['id'] == todo_id:
                t['done'] = True
                await query.edit_message_text(f"✅ Done: {t['text']}")
                break
    
    if data.startswith("delete_"):
        todo_id = int(data.split("_")[1])
        if user_id in user_todos:
            user_todos[user_id] = [t for t in user_todos[user_id] if t['id'] != todo_id]
            await query.edit_message_text("🗑️ Deleted")

# ========== ERROR ==========

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ Error occurred")

# ========== MAIN ==========

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("reminders", view_reminders))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("mytodos", view_todos))
    app.add_handler(CommandHandler("done", done_todo))
    app.add_handler(CommandHandler("delete", delete_todo))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_time))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_todo))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
