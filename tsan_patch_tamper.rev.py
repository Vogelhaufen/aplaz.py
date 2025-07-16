"""
Purpose: Input validation functions
কেন প্রয়োজন: User input validation centralized রাখার জন্য
"""

import re
from config.constants import MAX_FILE_SIZE, SUPPORTED_FILE_TYPES

def is_valid_group_id(group_id: str) -> bool:
    """Validate group ID format"""
    return bool(re.match(r'^-\d+$', group_id))

def is_valid_channel_id(channel_id: str) -> bool:
    """Validate channel ID format"""
    return bool(re.match(r'^-100\d+$', channel_id))

def is_valid_file_id(file_id: str) -> bool:
    """Validate file ID format"""
    return file_id.startswith("FILE_") and len(file_id) > 10

def is_valid_batch_id(batch_id: str) -> bool:
    """Validate batch ID format"""
    return batch_id.startswith("BATCH_") and len(batch_id) > 11

def is_valid_password(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 6:
        return False
    # At least one letter and one number
    return bool(re.search(r'[A-Za-z]', password)) and bool(re.search(r'[0-9]', password))

def validate_file_size(size: int) -> bool:
    """Validate file size"""
    return 0 < size <= MAX_FILE_SIZE

def validate_file_extension(filename: str) -> bool:
    """Validate file extension"""
    if not filename:
        return True
    
    extension = filename.split('.')[-1].lower()
    for file_type, extensions in SUPPORTED_FILE_TYPES.items():
        if extension in extensions:
            return True
    return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safety"""
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    return filename