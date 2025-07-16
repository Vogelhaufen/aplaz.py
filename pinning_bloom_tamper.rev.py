"""
Purpose: Inline keyboard markups
কেন প্রয়োজন: Reusable keyboard layouts
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(is_authorized: bool = False):
    """Get main menu keyboard"""
    if is_authorized:
        keyboard = [
            [
                InlineKeyboardButton("📁 Upload File", callback_data="start_upload"),
                InlineKeyboardButton("📦 Batch Upload", callback_data="start_batch")
            ],
            [
                InlineKeyboardButton("📊 My Stats", callback_data="show_stats"),
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")
            ]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📥 Download Files", callback_data="download_help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Get cancel button keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])