"""
Utility functions for validation and file handling
"""
import re
import hashlib
from typing import List
from pathlib import Path
from ..config import settings


def validate_file_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """
    Validate file extension
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed extensions (defaults to settings)
    
    Returns:
        True if extension is allowed, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = settings.get_allowed_extensions_list()
    
    file_ext = Path(filename).suffix.lower()
    # Check if the file extension matches any of the allowed extensions
    return file_ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int = None) -> bool:
    """
    Validate file size
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes (defaults to settings)
    
    Returns:
        True if file size is within limit, False otherwise
    """
    if max_size is None:
        max_size = settings.max_file_size
    
    return file_size <= max_size


def generate_scheme_id(scheme_name: str, source: str = "") -> str:
    """
    Generate a unique scheme ID from scheme name
    
    Args:
        scheme_name: Name of the scheme
        source: Source of the scheme (optional)
    
    Returns:
        Unique scheme ID
    """
    # Clean the scheme name
    clean_name = re.sub(r'[^\w\s-]', '', scheme_name.lower())
    
    # Replace spaces and hyphens with underscores
    clean_name = re.sub(r'[\s-]+', '_', clean_name)
    
    # Remove leading/trailing underscores
    clean_name = clean_name.strip('_')
    
    # Add source prefix if provided
    if source:
        source_clean = re.sub(r'[^\w]', '', source.lower())
        clean_name = f"{source_clean}_{clean_name}"
    
    # Ensure the ID is not too long
    if len(clean_name) > 50:
        clean_name = clean_name[:50]
    
    # Add hash suffix for uniqueness
    hash_suffix = hashlib.md5(scheme_name.encode()).hexdigest()[:8]
    scheme_id = f"{clean_name}_{hash_suffix}"
    
    return scheme_id


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(unsafe_chars, '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = 255 - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def validate_scheme_name(scheme_name: str) -> bool:
    """
    Validate scheme name
    
    Args:
        scheme_name: Name to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not scheme_name or not scheme_name.strip():
        return False
    
    # Check length
    if len(scheme_name.strip()) < 3 or len(scheme_name.strip()) > 200:
        return False
    
    # Check for valid characters (allow letters, numbers, spaces, hyphens, parentheses)
    if not re.match(r'^[a-zA-Z0-9\s\-\(\)\.]+$', scheme_name):
        return False
    
    return True


def validate_user_profile_data(profile_data: dict) -> List[str]:
    """
    Validate user profile data and return list of validation errors
    
    Args:
        profile_data: Dictionary containing profile data
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['age', 'gender', 'occupation']
    for field in required_fields:
        if field not in profile_data or profile_data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Age validation
    if 'age' in profile_data and profile_data['age'] is not None:
        try:
            age = int(profile_data['age'])
            if age < 0 or age > 150:
                errors.append("Age must be between 0 and 150")
        except (ValueError, TypeError):
            errors.append("Age must be a valid number")
    
    # Gender validation
    if 'gender' in profile_data and profile_data['gender'] is not None:
        valid_genders = ['male', 'female', 'other', 'prefer_not_to_say']
        if profile_data['gender'].lower() not in valid_genders:
            errors.append(f"Gender must be one of: {', '.join(valid_genders)}")
    
    # Income validation
    if 'income' in profile_data and profile_data['income'] is not None:
        try:
            income = float(profile_data['income'])
            if income < 0:
                errors.append("Income cannot be negative")
        except (ValueError, TypeError):
            errors.append("Income must be a valid number")
    
    # State validation (if provided)
    if 'state' in profile_data and profile_data['state'] is not None:
        # Basic validation for Indian state codes
        state = profile_data['state'].upper()
        if len(state) != 2 or not state.isalpha():
            errors.append("State must be a 2-letter code")
    
    return errors


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def extract_text_snippet(text: str, max_length: int = 200) -> str:
    """
    Extract a snippet of text for display purposes
    
    Args:
        text: Full text
        max_length: Maximum length of snippet
    
    Returns:
        Text snippet
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    snippet = text[:max_length]
    last_space = snippet.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can break at a reasonable word boundary
        snippet = snippet[:last_space]
    
    return snippet + "..."
