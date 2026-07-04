import os
import logging
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables!")

# Store reminders in memory (will reset on bot restart)
# For production, consider using a database
user_reminders = {}
user_todos = {}

# Helper function to format time
def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

# Helper function to parse time
def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    welcome_message = f"""
🌟 Welcome to Pocket Planner Bot! 🌟

Your personal productivity assistant! I can help you:
• Set reminders ⏰
• Manage your to-do list ✅
• Stay organized 📋

📌 Commands:
/remind - Set a reminder
/todo - Manage your to-do list
/mytodos - View your todos
/help - Show all commands

Let's boost your productivity together! 🚀
"""
    await update.message.reply_text(welcome_message)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Available Commands:**

/start - Start the bot
/help - Show this help message
/remind - Set a reminder
/todo - Manage your to-do list
/mytodos - View all your todos
/done - Mark a todo as done
/delete - Delete a todo
/reminders - View all your reminders
/cancel - Cancel any operation

**How to set a reminder:**
1. Type /remind
2. Enter your reminder message
3. Enter the time (format: YYYY-MM-DD HH:MM)

**Example:** 
/remind
Meeting with team
2026-07-05 15:30

Stay productive! 💪
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

# Reminder command - step 1: ask for message
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['reminder_step'] = 'waiting_for_message'
    await update.message.reply_text(
        "📝 Please enter your reminder message:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_reminder")]
        ])
    )

# Handle reminder message input
async def handle_reminder_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('reminder_step') == 'waiting_for_message':
        context.user_data['reminder_message'] = update.message.text
        context.user_data['reminder_step'] = 'waiting_for_time'
        await update.message.reply_text(
            "⏰ Please enter the time for your reminder (format: YYYY-MM-DD HH:MM)\n\nExample: 2026-07-05 15:30",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_reminder")]
            ])
        )

# Handle reminder time input
async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('reminder_step') == 'waiting_for_time':
        time_str = update.message.text
        reminder_time = parse_time(time_str)
        
        if reminder_time is None:
            await update.message.reply_text(
                "❌ Invalid time format! Please use: YYYY-MM-DD HH:MM\nExample: 2026-07-05 15:30"
            )
            return
        
        if reminder_time < datetime.now():
            await update.message.reply_text("❌ Time must be in the future!")
            return
        
        # Store the reminder
        message = context.user_data.get('reminder_message', 'No message')
        if user_id not in user_reminders:
            user_reminders[user_id] = []
        
        reminder_id = len(user_reminders[user_id]) + 1
        reminder = {
            'id': reminder_id,
            'message': message,
            'time': reminder_time,
            'created_at': datetime.now()
        }
        user_reminders[user_id].append(reminder)
        
        # Clear the step
        context.user_data['reminder_step'] = None
        context.user_data['reminder_message'] = None
        
        await update.message.reply_text(
            f"✅ Reminder set successfully!\n\n📝 Message: {message}\n⏰ Time: {format_time(reminder_time)}\n🆔 ID: {reminder_id}"
        )
        
        # Schedule the reminder notification
        schedule_reminder(update, context, user_id, reminder_id, reminder)

# Schedule reminder (simple check using asyncio)
def schedule_reminder(update, context, user_id, reminder_id, reminder):
    async def send_reminder():
        await asyncio.sleep((reminder['time'] - datetime.now()).total_seconds())
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏰ REMINDER! ⏰\n\n{reminder['message']}\n\nSet for: {format_time(reminder['time'])}"
            )
            # Remove the reminder after sending
            if user_id in user_reminders:
                user_reminders[user_id] = [r for r in user_reminders[user_id] if r['id'] != reminder_id]
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
    
    # Create task for the reminder
    asyncio.create_task(send_reminder())

# View reminders
async def view_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_reminders or not user_reminders[user_id]:
        await update.message.reply_text("📭 You have no reminders set.")
        return
    
    reminders = user_reminders[user_id]
    message = "📋 **Your Reminders:**\n\n"
    for r in reminders:
        message += f"🆔 {r['id']}: {r['message']}\n   ⏰ {format_time(r['time'])}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# Todo command
async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['todo_step'] = 'waiting_for_todo'
    await update.message.reply_text(
        "📝 Please enter your todo item:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_todo")]
        ])
    )

# Handle todo input
async def handle_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('todo_step') == 'waiting_for_todo':
        todo_text = update.message.text
        
        if user_id not in user_todos:
            user_todos[user_id] = []
        
        todo_id = len(user_todos[user_id]) + 1
        todo_item = {
            'id': todo_id,
            'text': todo_text,
            'done': False,
            'created_at': datetime.now()
        }
        user_todos[user_id].append(todo_item)
        
        context.user_data['todo_step'] = None
        
        await update.message.reply_text(f"✅ Todo added successfully!\n\n📝 {todo_text}\n🆔 ID: {todo_id}")

# View todos
async def view_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 Your todo list is empty!")
        return
    
    todos = user_todos[user_id]
    message = "📋 **Your Todos:**\n\n"
    for t in todos:
        status = "✅" if t['done'] else "⬜"
        message += f"{status} 🆔 {t['id']}: {t['text']}\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# Mark todo as done
async def done_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 You have no todos!")
        return
    
    # Show todos that are not done
    pending_todos = [t for t in user_todos[user_id] if not t['done']]
    if not pending_todos:
        await update.message.reply_text("🎉 All your todos are done!")
        return
    
    keyboard = []
    for t in pending_todos:
        keyboard.append([InlineKeyboardButton(f"{t['text']}", callback_data=f"done_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_done")])
    
    await update.message.reply_text(
        "✅ Select a todo to mark as done:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Delete todo
async def delete_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_todos or not user_todos[user_id]:
        await update.message.reply_text("📭 You have no todos!")
        return
    
    keyboard = []
    for t in user_todos[user_id]:
        keyboard.append([InlineKeyboardButton(f"{t['text']}", callback_data=f"delete_{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")])
    
    await update.message.reply_text(
        "🗑️ Select a todo to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "cancel_reminder":
        context.user_data['reminder_step'] = None
        context.user_data['reminder_message'] = None
        await query.edit_message_text("❌ Reminder cancelled.")
        return
    
    elif data == "cancel_todo":
        context.user_data['todo_step'] = None
        await query.edit_message_text("❌ Todo cancelled.")
        return
    
    elif data == "cancel_done":
        await query.edit_message_text("❌ Cancelled.")
        return
    
    elif data == "cancel_delete":
        await query.edit_message_text("❌ Cancelled.")
        return
    
    elif data.startswith("done_"):
        todo_id = int(data.split("_")[1])
        if user_id in user_todos:
            for t in user_todos[user_id]:
                if t['id'] == todo_id:
                    t['done'] = True
                    await query.edit_message_text(f"✅ Todo marked as done: {t['text']}")
                    break
    
    elif data.startswith("delete_"):
        todo_id = int(data.split("_")[1])
        if user_id in user_todos:
            user_todos[user_id] = [t for t in user_todos[user_id] if t['id'] != todo_id]
            await query.edit_message_text(f"🗑️ Todo deleted.")

# Ping command for health check
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot is alive and running!")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ An error occurred. Please try again.")

# Main function
def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("remind", remind))
    application.add_handler(CommandHandler("reminders", view_reminders))
    application.add_handler(CommandHandler("todo", todo))
    application.add_handler(CommandHandler("mytodos", view_todos))
    application.add_handler(CommandHandler("done", done_todo))
    application.add_handler(CommandHandler("delete", delete_todo))
    application.add_handler(CommandHandler("ping", ping))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_time))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_todo))
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
