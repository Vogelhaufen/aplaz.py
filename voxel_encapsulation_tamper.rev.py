"""
Purpose: Handle /start command and deep links
কেন প্রয়োজন: Bot এর main entry point এবং deep link handling
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

# Import from our modules
from utils.decorators import authorized_only
from services.file_service import get_file_from_db
from services.batch_service import get_batch_from_db, get_batch_files
from handlers.channel_handlers import check_user_membership, get_user_force_subscribe_channels, log_subscription_analytics
from handlers.settings_handlers import check_file_protection
from utils.state_manager import state_manager
from config.constants import AUTHORIZED_USERS

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Check if deep link
    if context.args and len(context.args) > 0:
        await handle_deep_link(update, context, context.args[0])
        return
    
    # Check if authorized user
    is_authorized = user_id in AUTHORIZED_USERS
    
    if is_authorized:
        # Authorized user menu
        keyboard = [
            [
                InlineKeyboardButton("📁 Upload File", callback_data="start_upload"),
                InlineKeyboardButton("📦 Batch Upload", callback_data="start_batch")
            ],
            [
                InlineKeyboardButton("📊 My Stats", callback_data="show_stats"),
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")
            ],
            [
                InlineKeyboardButton("📺 Channels", callback_data="manage_channels"),
                InlineKeyboardButton("🗄️ Database", callback_data="manage_database")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
👋 **Welcome back, {user.first_name}!**

You are an **Authorized User** with full access.

**Quick Commands:**
• /link - Upload single file
• /batch - Upload multiple files
• /database - Set database group
• /addchannel - Add force subscribe channel
• /protect - Enable file protection
• /autodelete - Set auto-delete timer

**Your Stats:**
• Total Files: Loading...
• Total Batches: Loading...
• Storage Used: Loading...

Select an option below to get started:
        """
    else:
        # Non-authorized user menu
        keyboard = [
            [InlineKeyboardButton("📥 Download Files", callback_data="download_help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
👋 **Welcome, {user.first_name}!**

I'm a **File Store Bot** that helps store and share files securely.

**As a user, you can:**
• Download files using direct links
• Access shared batches
• View file information

**To download files:**
• Click on a shared link
• Or send a file/batch ID

**Need help?** Contact the bot admin.
        """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Load stats for authorized users
    if is_authorized:
        await load_user_stats(update, context, user_id)

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, param: str):
    """Handle deep link parameters"""
    user_id = update.effective_user.id
    
    # Check if it's a file or batch
    if param.startswith("FILE_"):
        await send_file_with_checks(update, context, param)
    elif param.startswith("BATCH_"):
        await send_batch_with_checks(update, context, param)
    else:
        await update.message.reply_text(
            "❌ **Invalid Link!**\n\n"
            "This link is not valid or has expired.",
            parse_mode='Markdown'
        )

async def send_file_with_checks(update: Update, context: ContextTypes.DEFAULT_TYPE, unique_id: str):
    """Send file with all security checks"""
    user_id = update.effective_user.id
    
    # Get file from database
    file_doc = get_file_from_db(unique_id)
    
    if not file_doc:
        await update.message.reply_text(
            "❌ **File Not Found!**\n\n"
            "This file doesn't exist or has been deleted.",
            parse_mode='Markdown'
        )
        return
    
    # Get file owner's settings
    owner_id = file_doc['uploaded_by']
    
    # Check force subscribe channels
    channels = await get_user_force_subscribe_channels(owner_id)
    not_joined = []
    
    for channel in channels:
        is_member = await check_user_membership(context, user_id, channel['channel_id'])
        if not is_member:
            not_joined.append(channel)
        else:
            # Log analytics
            await log_subscription_analytics(user_id, channel['channel_id'], 'joined')
    
    if not_joined:
        # Create join buttons
        keyboard = []
        for channel in not_joined:
            keyboard.append([InlineKeyboardButton(
                f"📺 Join {channel['channel_title']}", 
                url=f"https://t.me/{channel['channel_title'].replace('@', '')}"
            )])
        
        keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data=f"check_joined_{unique_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ **Join Required Channels First!**\n\n"
            "You must join all channels below to access this file:\n\n" +
            "\n".join([f"• {ch['channel_title']}" for ch in not_joined]) +
            "\n\nAfter joining, click 'I've Joined' button.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Check file protection
    protection = await check_file_protection(owner_id)
    if protection:
        # Set state to wait for password
        state_manager.set_user_state(user_id, f"waiting_for_file_password_{unique_id}")
        
        await update.message.reply_text(
            "🔒 **This file is password protected!**\n\n"
            "Please enter the password to access this file:",
            parse_mode='Markdown'
        )
        return
    
    # All checks passed, send file
    await send_file(update, context, file_doc)

async def send_batch_with_checks(update: Update, context: ContextTypes.DEFAULT_TYPE, batch_id: str):
    """Send batch with all security checks"""
    user_id = update.effective_user.id
    
    # Get batch from database
    batch_doc = get_batch_from_db(batch_id)
    
    if not batch_doc:
        await update.message.reply_text(
            "❌ **Batch Not Found!**\n\n"
            "This batch doesn't exist or has been deleted.",
            parse_mode='Markdown'
        )
        return
    
    # Get batch owner's settings
    owner_id = batch_doc['uploaded_by']
    
    # Check force subscribe channels
    channels = await get_user_force_subscribe_channels(owner_id)
    not_joined = []
    
    for channel in channels:
        is_member = await check_user_membership(context, user_id, channel['channel_id'])
        if not is_member:
            not_joined.append(channel)
    
    if not_joined:
        # Create join buttons
        keyboard = []
        for channel in not_joined:
            keyboard.append([InlineKeyboardButton(
                f"📺 Join {channel['channel_title']}", 
                url=f"https://t.me/{channel['channel_title'].replace('@', '')}"
            )])
        
        keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data=f"check_joined_batch_{batch_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ **Join Required Channels First!**\n\n"
            "You must join all channels below to access this batch:\n\n" +
            "\n".join([f"• {ch['channel_title']}" for ch in not_joined]) +
            "\n\nAfter joining, click 'I've Joined' button.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Check file protection
    protection = await check_file_protection(owner_id)
    if protection:
        # Set state to wait for password
        state_manager.set_user_state(user_id, f"waiting_for_batch_password_{batch_id}")
        
        await update.message.reply_text(
            "🔒 **This batch is password protected!**\n\n"
            "Please enter the password to access this batch:",
            parse_mode='Markdown'
        )
        return
    
    # All checks passed, send batch
    await send_batch(update, context, batch_doc)

async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_doc: dict):
    """Send file to user"""
    try:
        file_id = file_doc['file_id']
        file_type = file_doc['file_type']
        file_name = file_doc.get('file_name', 'Unknown')
        
        caption = f"""
📄 **File Details:**
• Name: `{file_name}`
• Type: `{file_type.upper()}`
• Size: `{file_doc['file_size'] / 1024 / 1024:.2f} MB`
• Uploaded: `{file_doc['upload_date'].strftime('%d/%m/%Y')}`
• Downloads: `{file_doc.get('download_count', 0) + 1}`

🔗 **File ID:** `{file_doc['unique_id']}`
        """
        
        # Send based on file type
        if file_type == 'document':
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif file_type == 'video':
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif file_type == 'photo':
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif file_type == 'audio':
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif file_type == 'voice':
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        
        # Log analytics
        await log_subscription_analytics(
            update.effective_user.id, 
            file_doc['uploaded_by'], 
            'accessed_file'
        )
        
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text(
            "❌ **Error sending file!**\n\n"
            "Please try again later or contact admin.",
            parse_mode='Markdown'
        )

async def send_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, batch_doc: dict):
    """Send batch files to user"""
    try:
        batch_files = get_batch_files(batch_doc['batch_id'])
        
        if not batch_files:
            await update.message.reply_text(
                "❌ **No files found in this batch!**",
                parse_mode='Markdown'
            )
            return
        
        # Send batch info
        batch_info = f"""
📦 **Batch Details:**
• Batch ID: `{batch_doc['batch_id']}`
• Total Files: `{len(batch_files)}`
• Total Size: `{batch_doc['total_size']:.2f} MB`
• Created: `{batch_doc['created_date'].strftime('%d/%m/%Y')}`
• Downloads: `{batch_doc.get('download_count', 0) + 1}`

**Sending {len(batch_files)} files...**
        """
        
        await update.message.reply_text(batch_info, parse_mode='Markdown')
        
        # Send each file
        for i, file_doc in enumerate(batch_files, 1):
            file_doc['file_name'] = f"[{i}/{len(batch_files)}] {file_doc.get('file_name', 'Unknown')}"
            await send_file(update, context, file_doc)
        
        await update.message.reply_text(
            f"✅ **Batch sent successfully!**\n\n"
            f"Total {len(batch_files)} files sent.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error sending batch: {e}")
        await update.message.reply_text(
            "❌ **Error sending batch!**\n\n"
            "Please try again later or contact admin.",
            parse_mode='Markdown'
        )

async def load_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Load and display user statistics"""
    try:
        from services.file_service import get_user_files_count
        from services.batch_service import get_user_batches_count
        from database.collections import collection
        
        # Get stats
        total_files = get_user_files_count(user_id)
        total_batches = get_user_batches_count(user_id)
        
        # Calculate storage
        pipeline = [
            {"$match": {"uploaded_by": user_id}},
            {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
        ]
        result = list(collection.aggregate(pipeline))
        total_storage = result[0]['total_size'] / (1024 * 1024) if result else 0
        
        # Update message with stats
        stats_text = f"""
📊 **Your Statistics:**
• Total Files: `{total_files}`
• Total Batches: `{total_batches}`
• Storage Used: `{total_storage:.2f} MB`
        """
        
        # This would update the original message if we had stored the message_id
        # For now, just log the stats
        logger.info(f"User {user_id} stats loaded: Files={total_files}, Batches={total_batches}, Storage={total_storage:.2f}MB")
        
    except Exception as e:
        logger.error(f"Error loading user stats: {e}")