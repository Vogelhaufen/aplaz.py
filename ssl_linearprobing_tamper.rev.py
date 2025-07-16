"""
Purpose: Handle all inline keyboard button callbacks
কেন প্রয়োজন: সব button interactions centralized রাখার জন্য
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

# Import from our modules
from utils.state_manager import state_manager
from utils.decorators import authorized_only
from handlers.batch_handlers import batch_command, finish_batch_command, cancel_batch_command
from handlers.settings_handlers import enable_protection, disable_protection, set_autodelete, disable_autodelete
from services.file_service import delete_database_group
from database.collections import force_subscribe_collection

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback handler - routes to appropriate handlers"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Database group callbacks
    if data == "replace_database_group":
        await handle_replace_database_group(update, context)
    elif data == "cancel_database_setup":
        await handle_cancel_database_setup(update, context)
    elif data == "confirm_remove_database":
        await handle_confirm_remove_database(update, context)
    elif data == "cancel_remove_database":
        await handle_cancel_remove_database(update, context)
    
    # Batch callbacks
    elif data == "start_batch":
        await handle_start_batch(update, context)
    elif data == "finish_batch":
        await finish_batch_command(update, context)
    elif data == "cancel_batch":
        await cancel_batch_command(update, context)
    
    # File upload callbacks
    elif data == "start_upload":
        await handle_start_upload(update, context)
    
    # Protection callbacks
    elif data == "enable_protection":
        await handle_enable_protection(update, context)
    elif data == "disable_protection":
        await handle_disable_protection(update, context)
    elif data == "update_protection":
        await handle_update_protection(update, context)
    elif data == "cancel_protection":
        await handle_cancel_protection(update, context)
    
    # Auto-delete callbacks
    elif data.startswith("set_autodelete_"):
        hours = int(data.split("_")[2])
        await handle_set_autodelete(update, context, hours)
    elif data == "change_autodelete_timer":
        await handle_change_autodelete_timer(update, context)
    elif data == "disable_autodelete":
        await handle_disable_autodelete(update, context)
    elif data == "cancel_autodelete":
        await handle_cancel_autodelete(update, context)
    
    # Channel callbacks
    elif data.startswith("delete_channel_"):
        channel_id = int(data.split("_")[2])
        await handle_delete_channel(update, context, channel_id)
    elif data == "cancel_delete":
        await handle_cancel_delete(update, context)

# Database Group Callbacks
async def handle_replace_database_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle database group replacement"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Set state for new database group
    state_manager.set_user_state(user_id, "waiting_for_database_group_id")
    
    await query.edit_message_text(
        "📁 **Replace Database Group**\n\n"
        "Please follow these steps to set a new database group:\n\n"
        "1️⃣ Add me to your new **GROUP** as a **Member** first\n"
        "2️⃣ Then **promote me to Admin** with message sending permission\n"
        "3️⃣ I will automatically send the Group ID in that group\n"
        "4️⃣ Copy that ID and send it to me here for verification\n\n"
        "**Note:** Your old database group will be replaced.",
        parse_mode='Markdown'
    )

async def handle_cancel_database_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel database group setup"""
    query = update.callback_query
    await query.edit_message_text(
        "❌ **Database Group Setup Cancelled**\n\n"
        "Your current database group remains unchanged.",
        parse_mode='Markdown'
    )

async def handle_confirm_remove_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm database group removal"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if delete_database_group(user_id):
        await query.edit_message_text(
            "✅ **Database Group Removed Successfully!**\n\n"
            "You'll need to set a new database group to upload files.\n"
            "Use /database to set a new group.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ **Failed to remove database group!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def handle_cancel_remove_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel database group removal"""
    query = update.callback_query
    await query.edit_message_text(
        "❌ **Database Group Removal Cancelled**\n\n"
        "Your database group remains active.",
        parse_mode='Markdown'
    )

# Batch Callbacks
async def handle_start_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new batch upload"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Clear any existing batch state
    state_manager.clear_batch_state(user_id)
    
    # Start new batch
    await batch_command(update, context)

# File Upload Callbacks
async def handle_start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new file upload"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Set state for file upload
    state_manager.set_user_state(user_id, "waiting_for_file")
    
    await query.edit_message_text(
        "📁 **Ready for File Upload!**\n\n"
        "Send your file to your database group now.\n"
        "I'll send you the link here in private chat.\n\n"
        "**Supported:** Documents, Videos, Photos, Audio, Voice messages",
        parse_mode='Markdown'
    )

# Protection Callbacks
async def handle_enable_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable file protection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Set state to wait for password
    state_manager.set_user_state(user_id, "waiting_for_protection_password")
    
    await query.edit_message_text(
        "🔒 **Set Protection Password**\n\n"
        "Please send a strong password for file protection.\n\n"
        "**Password Requirements:**\n"
        "• Minimum 6 characters\n"
        "• Mix of letters and numbers recommended\n"
        "• Avoid common passwords\n\n"
        "Send your password now:",
        parse_mode='Markdown'
    )

async def handle_disable_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable file protection"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if await disable_protection(user_id):
        await query.edit_message_text(
            "✅ **File Protection Disabled!**\n\n"
            "Your files are no longer password protected.\n"
            "Use /protect to enable protection again.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ **Failed to disable protection!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def handle_update_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update protection password"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Set state to wait for new password
    state_manager.set_user_state(user_id, "waiting_for_new_protection_password")
    
    await query.edit_message_text(
        "🔄 **Update Protection Password**\n\n"
        "Send your new password for file protection.\n\n"
        "**Note:** This will replace your current password.",
        parse_mode='Markdown'
    )

async def handle_cancel_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel protection setup"""
    query = update.callback_query
    await query.edit_message_text(
        "❌ **Protection Setup Cancelled**\n\n"
        "Your protection settings remain unchanged.",
        parse_mode='Markdown'
    )

# Auto-delete Callbacks
async def handle_set_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE, hours: int):
    """Set auto-delete timer"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if await set_autodelete(user_id, hours):
        await query.edit_message_text(
            f"✅ **Auto-Delete Enabled!**\n\n"
            f"Files will be automatically deleted after **{hours} hours**.\n\n"
            f"**Note:** This applies to all new files you upload.\n"
            f"Existing files are not affected.\n\n"
            f"Use /autodelete to change settings.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ **Failed to enable auto-delete!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def handle_change_autodelete_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change auto-delete timer"""
    query = update.callback_query
    
    keyboard = []
    for hours in [1, 6, 12, 24, 48, 72]:
        keyboard.append([InlineKeyboardButton(
            f"⏰ {hours} {'hour' if hours == 1 else 'hours'}", 
            callback_data=f"set_autodelete_{hours}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_autodelete")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ **Change Auto-Delete Timer**\n\n"
        "Select new timer for auto-delete:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_disable_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable auto-delete"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if await disable_autodelete(user_id):
        await query.edit_message_text(
            "✅ **Auto-Delete Disabled!**\n\n"
            "Files will no longer be automatically deleted.\n"
            "Use /autodelete to enable it again.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ **Failed to disable auto-delete!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def handle_cancel_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel auto-delete setup"""
    query = update.callback_query
    await query.edit_message_text(
        "❌ **Auto-Delete Setup Cancelled**\n\n"
        "Your auto-delete settings remain unchanged.",
        parse_mode='Markdown'
    )

# Channel Callbacks
async def handle_delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    """Delete force subscribe channel"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Update channel status
        force_subscribe_collection.update_one(
            {"user_id": user_id, "channel_id": channel_id},
            {"$set": {"is_active": False}}
        )
        
        await query.edit_message_text(
            "✅ **Channel Removed Successfully!**\n\n"
            "The channel has been removed from your force subscribe list.\n\n"
            "Use /addchannel to add new channels.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        await query.edit_message_text(
            "❌ **Failed to remove channel!**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def handle_cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel channel deletion"""
    query = update.callback_query
    await query.edit_message_text(
        "❌ **Channel Deletion Cancelled**\n\n"
        "No channels were removed.",
        parse_mode='Markdown'
    )