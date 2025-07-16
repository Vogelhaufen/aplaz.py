"""
Purpose: Force subscribe channel management handlers
কেন প্রয়োজন: Channel subscription functionality আলাদা module এ রাখা
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging

# Import from our modules
from utils.state_manager import state_manager
from utils.decorators import authorized_only
from database.collections import force_subscribe_collection, analytics_collection

logger = logging.getLogger(__name__)

@authorized_only
async def addchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addchannel command"""
    user_id = update.effective_user.id
    
    # Set state in MongoDB
    state_manager.set_user_state(user_id, "waiting_for_channel_id")
    
    await update.message.reply_text(
        "📺 **Force Subscribe Channel Setup**\n\n"
        "To add a Force Subscribe channel, please follow these steps:\n\n"
        "1️⃣ Add me to your channel/group as a **Member** first\n"
        "2️⃣ Then **promote me to Admin** with necessary permissions\n"
        "3️⃣ I will automatically send the Channel/Group ID in that channel/group\n"
        "4️⃣ Copy that ID and send it to me here for verification\n\n"
        "**⚠️ Important Process:**\n"
        "• Add as **member** first, then promote to admin\n"
        "• Direct admin addition may not work properly\n\n"
        "**Simple Process:**\n"
        "• Add bot as member → Promote to admin → Copy ID → Send to bot",
        parse_mode='Markdown'
    )

async def handle_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id_text: str):
    """
    Handle channel ID verification
    Called when user state is 'waiting_for_channel_id'
    """
    user_id = update.effective_user.id
    
    if not (channel_id_text.startswith('-100') or channel_id_text.startswith('-')):
        await update.message.reply_text(
            "❌ **Invalid Channel ID Format**\n"
            "Please send a valid channel/group ID (starts with -100 or -).",
            parse_mode='Markdown'
        )
        return
    
    try:
        channel_id = int(channel_id_text)
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid Channel ID**\n"
            "Please send a valid numeric channel/group ID.",
            parse_mode='Markdown'
        )
        return
    
    # Check if bot is admin
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ **Bot Not Admin**\n"
                "Please make me an admin in the channel with member viewing permission.\n\n"
                "**Fix Problem: Proper Setup Process:**\n"
                "1. Add me as **member** first\n"
                "2. Then **promote to admin**\n"
                "3. Give necessary permissions\n\n"
                "**Note:** Adding directly as admin may not work properly.",
                parse_mode='Markdown'
            )
            return
    except Exception as e:
        logger.error(f"Error checking bot admin status: {e}")
        await update.message.reply_text(
            "❌ **Channel Not Found or Access Denied**\n"
            "I cannot access this channel. Make sure:\n"
            "• The ID is correct\n"
            "• I am added as admin\n"
            "• Add as member first, then promote to admin",
            parse_mode='Markdown'
        )
        return
    
    # Check if already exists
    existing = force_subscribe_collection.find_one({"user_id": user_id, "channel_id": channel_id})
    if existing:
        await update.message.reply_text(
            "❌ **Already Added**\n"
            "This channel is already in your Force Subscribe list.",
            parse_mode='Markdown'
        )
        return
    
    # Get channel info
    try:
        chat = await context.bot.get_chat(channel_id)
        channel_title = chat.title or "No Title"
        try:
            member_count = await context.bot.get_chat_member_count(channel_id)
        except:
            member_count = "Unknown"
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        channel_title = "Unknown"
        member_count = "Unknown"
    
    # Save to database
    force_subscribe_collection.insert_one({
        "user_id": user_id,
        "channel_id": channel_id,
        "channel_title": channel_title,
        "is_active": True,
        "set_date": datetime.now()
    })
    
    # Clear user state
    state_manager.clear_user_state(user_id)
    
    await update.message.reply_text(
        f"✅ **Force Subscribe Channel Added Successfully!**\n\n"
        f"📺 **Channel Details:**\n"
        f"• Name: `{channel_title}`\n"
        f"• ID: `{channel_id}`\n"
        f"• Members: `{member_count}`\n"
        f"• Type: `{chat.type}`\n\n"
        f"🎉 **All Set!** Users must now join this channel to access your files.\n\n"
        f"**Manage Channels:**\n"
        f"/listchannels - View all channels\n"
        f"/removechannel - Remove a channel\n"
        f"/channelstats - View analytics",
        parse_mode='Markdown'
    )

@authorized_only
async def listchannels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all force subscribe channels for user"""
    user_id = update.effective_user.id
    
    channels = list(force_subscribe_collection.find({
        "user_id": user_id,
        "is_active": True
    }))
    
    if not channels:
        await update.message.reply_text(
            "📺 **No Force Subscribe Channels**\n\n"
            "You haven't added any force subscribe channels yet.\n"
            "Use /addchannel to add your first channel!",
            parse_mode='Markdown'
        )
        return
    
    channel_list = "📺 **Your Force Subscribe Channels:**\n\n"
    for i, channel in enumerate(channels, 1):
        status = "🟢 Active" if channel['is_active'] else "🔴 Inactive"
        channel_list += f"{i}. **{channel['channel_title']}**\n"
        channel_list += f"   ID: `{channel['channel_id']}`\n"
        channel_list += f"   Status: {status}\n"
        channel_list += f"   Added: {channel['set_date'].strftime('%d/%m/%Y')}\n\n"
    
    channel_list += "**Commands:**\n"
    channel_list += "/removechannel - Remove a channel\n"
    channel_list += "/channelstats - View analytics"
    
    await update.message.reply_text(channel_list, parse_mode='Markdown')

@authorized_only
async def removechannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removechannel command"""
    user_id = update.effective_user.id
    
    channels = list(force_subscribe_collection.find({
        "user_id": user_id,
        "is_active": True
    }))
    
    if not channels:
        await update.message.reply_text(
            "📺 **No Force Subscribe Channels Found**\n\n"
            "You haven't added any channels yet.\n"
            "Use /addchannel to add your first channel!",
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(
            f"🗑️ Delete {channel['channel_title']}", 
            callback_data=f"delete_channel_{channel['channel_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    channel_text = "📺 **Your Force Subscribe Channels:**\n\n"
    channel_text += "Select a channel to remove:\n\n"
    
    for i, channel in enumerate(channels, 1):
        channel_text += f"{i}. **{channel['channel_title']}**\n"
        channel_text += f"   ID: `{channel['channel_id']}`\n\n"
    
    channel_text += "⚠️ **Warning:** Deleted channels cannot be recovered!"
    
    await update.message.reply_text(
        channel_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@authorized_only
async def channelstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show channel analytics"""
    user_id = update.effective_user.id
    
    channels = list(force_subscribe_collection.find({
        "user_id": user_id,
        "is_active": True
    }))
    
    if not channels:
        await update.message.reply_text(
            "📊 **No Analytics Available**\n\n"
            "Add force subscribe channels first to see analytics.",
            parse_mode='Markdown'
        )
        return
    
    stats_text = "📊 **Channel Analytics:**\n\n"
    
    for channel in channels:
        channel_id = channel['channel_id']
        
        # Get analytics
        subscription_count = analytics_collection.count_documents({
            "channel_id": channel_id,
            "action": "joined"
        })
        
        file_access_count = analytics_collection.count_documents({
            "channel_id": channel_id,
            "action": "accessed_file"
        })
        
        stats_text += f"📺 **{channel['channel_title']}**\n"
        stats_text += f"   Subscriptions: `{subscription_count}`\n"
        stats_text += f"   File Accesses: `{file_access_count}`\n"
        stats_text += f"   Status: {'🟢 Active' if channel['is_active'] else '🔴 Inactive'}\n\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def check_user_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int, channel_id: int) -> bool:
    """Check if user is member of a channel"""
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def get_user_force_subscribe_channels(user_id: int) -> list:
    """Get all active force subscribe channels for a user"""
    try:
        channels = list(force_subscribe_collection.find({
            "user_id": user_id,
            "is_active": True
        }))
        return channels
    except Exception as e:
        logger.error(f"Error getting force subscribe channels: {e}")
        return []

async def log_subscription_analytics(user_id: int, channel_id: int, action: str):
    """Log subscription analytics"""
    try:
        existing = analytics_collection.find_one({
            "user_id": user_id,
            "channel_id": channel_id,
            "action": action
        })
        
        if not existing:
            analytics_collection.insert_one({
                "user_id": user_id,
                "channel_id": channel_id,
                "action": action,
                "timestamp": datetime.now()
            })
    except Exception as e:
        logger.error(f"Error logging analytics: {e}")