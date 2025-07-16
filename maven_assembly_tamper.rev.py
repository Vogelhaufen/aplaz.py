"""
Purpose: Main bot application - entry point
কেন প্রয়োজন: Bot initialization এবং সব handlers register করার জন্য
"""

import logging
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters
)

# Import configurations
from config.settings import BOT_TOKEN
from config.constants import AUTHORIZED_USERS

# Import database
from database.connection import db

# Import handlers
from handlers.start import start_command
from handlers.file_handlers import link_command, handle_file
from handlers.batch_handlers import batch_command
from handlers.database_handlers import (
    database_command, 
    showdatabase_command, 
    removedatabase_command
)
from handlers.channel_handlers import (
    addchannel_command,
    listchannels_command,
    removechannel_command,
    channelstats_command
)
from handlers.settings_handlers import (
    protect_command,
    autodelete_command,
    showsettings_command
)
from handlers.callback_handlers import button_callback

# Import message handler
from handlers.message_handler import handle_message

# Import services
from services.cleanup_service import setup_cleanup_jobs

# Import utilities
from utils.state_manager import state_manager

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Error handler
async def error_handler(update: Update, context):
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **An error occurred!**\n\n"
                "Please try again later or contact the admin if the problem persists.",
                parse_mode='Markdown'
            )
    except:
        pass

# Bot added to group handler
async def bot_added_to_group(update: Update, context):
    """Handle when bot is added to a group"""
    if update.my_chat_member:
        chat = update.my_chat_member.chat
        new_status = update.my_chat_member.new_chat_member.status
        
        if new_status in ['member', 'administrator']:
            # Send group ID
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"👋 **Hello!**\n\n"
                         f"I've been added to this {'group' if chat.type in ['group', 'supergroup'] else 'channel'}.\n\n"
                         f"📍 **Chat Details:**\n"
                         f"• Name: `{chat.title}`\n"
                         f"• ID: `{chat.id}`\n"
                         f"• Type: `{chat.type}`\n\n"
                         f"**Copy the ID above and send it to me in private chat to complete setup.**",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending group ID: {e}")

# Help command
async def help_command(update: Update, context):
    """Show help message"""
    user_id = update.effective_user.id
    is_authorized = user_id in AUTHORIZED_USERS
    
    if is_authorized:
        help_text = """
📚 **Bot Commands:**

**File Management:**
• /start - Start the bot
• /link - Upload single file
• /batch - Upload multiple files
• /get <file_id> - Get file by ID

**Database Group:**
• /database - Set database group
• /showdatabase - Show current database
• /removedatabase - Remove database

**Force Subscribe:**
• /addchannel - Add force subscribe channel
• /listchannels - List all channels
• /removechannel - Remove a channel
• /channelstats - View channel analytics

**Settings:**
• /protect - File protection settings
• /autodelete - Auto-delete settings
• /showsettings - View all settings

**Other:**
• /help - Show this help message
• /stats - View your statistics
• /about - About this bot

**Tips:**
• Always set a database group first
• Files must be sent to database group
• Use batch upload for multiple files
• Enable protection for sensitive files
        """
    else:
        help_text = """
📚 **How to Use:**

• Click on shared links to download files
• Send file/batch IDs to get files
• Join required channels to access files

**Commands:**
• /start - Start the bot
• /help - Show this help
• /about - About this bot

**Need more access?** Contact the bot admin.
        """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Stats command
async def stats_command(update: Update, context):
    """Show user statistics"""
    user_id = update.effective_user.id
    
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text(
            "❌ **You are not authorized to use this command!**",
            parse_mode='Markdown'
        )
        return
    
    from services.file_service import get_user_files_count
    from services.batch_service import get_user_batches_count
    from database.collections import collection, force_subscribe_collection
    
    try:
        # Get stats
        total_files = get_user_files_count(user_id)
        total_batches = get_user_batches_count(user_id)
        total_channels = force_subscribe_collection.count_documents({
            "user_id": user_id,
            "is_active": True
        })
        
        # Calculate storage
        pipeline = [
            {"$match": {"uploaded_by": user_id}},
            {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
        ]
        result = list(collection.aggregate(pipeline))
        total_storage = result[0]['total_size'] / (1024 * 1024 * 1024) if result else 0  # In GB
        
        # Calculate downloads
        pipeline = [
            {"$match": {"uploaded_by": user_id}},
            {"$group": {"_id": None, "total_downloads": {"$sum": "$download_count"}}}
        ]
        result = list(collection.aggregate(pipeline))
        total_downloads = result[0]['total_downloads'] if result else 0
        
        stats_text = f"""
📊 **Your Statistics:**

**Storage:**
• Total Files: `{total_files}`
• Total Batches: `{total_batches}`
• Storage Used: `{total_storage:.2f} GB`

**Engagement:**
• Total Downloads: `{total_downloads}`
• Force Subscribe Channels: `{total_channels}`

**Average:**
• Downloads per File: `{total_downloads / total_files if total_files > 0 else 0:.1f}`
• Files per Batch: `{total_files / total_batches if total_batches > 0 else 0:.1f}`

Use /showsettings to view your current settings.
        """
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(
            "❌ **Error loading statistics!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

# About command
async def about_command(update: Update, context):
    """Show about message"""
    about_text = """
ℹ️ **About File Store Bot**

This bot helps you store and share files securely with advanced features.

**Features:**
✅ Unlimited file storage
✅ Batch upload support
✅ Force subscribe channels
✅ Password protection
✅ Auto-delete timer
✅ Clean group technology
✅ Analytics and statistics

**Security:**
🔒 Files stored securely
🔒 Password protection available
🔒 Private database groups
🔒 Authorized users only

**Developed with ❤️ using:**
• Python & python-telegram-bot
• MongoDB for data storage
• Advanced security features

**Version:** 2.0
**Last Updated:** December 2024
    """
    
    await update.message.reply_text(about_text, parse_mode='Markdown')

def main():
    """Main function to run the bot"""
    # Connect to database
    if not db.connect():
        logger.error("Failed to connect to database! Exiting...")
        return
    
    logger.info("Database connected successfully!")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # File handlers
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("batch", batch_command))
    
    # Database handlers
    application.add_handler(CommandHandler("database", database_command))
    application.add_handler(CommandHandler("showdatabase", showdatabase_command))
    application.add_handler(CommandHandler("removedatabase", removedatabase_command))
    
    # Channel handlers
    application.add_handler(CommandHandler("addchannel", addchannel_command))
    application.add_handler(CommandHandler("listchannels", listchannels_command))
    application.add_handler(CommandHandler("removechannel", removechannel_command))
    application.add_handler(CommandHandler("channelstats", channelstats_command))
    
    # Settings handlers
    application.add_handler(CommandHandler("protect", protect_command))
    application.add_handler(CommandHandler("autodelete", autodelete_command))
    application.add_handler(CommandHandler("showsettings", showsettings_command))
    
    # Message handler (for files and text)
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handle_message
    ))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Chat member updates (for group ID)
    application.add_handler(MessageHandler(
        filters.StatusUpdate.CHAT_MEMBER,
        bot_added_to_group
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Setup cleanup jobs
    setup_cleanup_jobs(application)
    
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")