"""File handling utilities for word list parsing and WAV file management"""

import os
import re
from typing import List, Tuple


def parse_word_list(text: str) -> List[str]:
    """
    Parse a word list from input text
    
    Supports:
    - Newline-separated words
    - Comma-separated words
    - Mixed separators
    
    Args:
        text: Input text containing words
        
    Returns:
        List of cleaned words
    """
    if not text or not text.strip():
        return []
    
    # Split by newlines and commas, then flatten
    words = []
    for line in text.split('\n'):
        # Split by comma as well
        line_words = [word.strip() for word in line.split(',')]
        words.extend(line_words)
    
    # Filter out empty strings and clean words
    cleaned_words = []
    for word in words:
        word = word.strip()
        if word:
            # Remove extra whitespace
            word = re.sub(r'\s+', ' ', word)
            cleaned_words.append(word)
    
    return cleaned_words


def sanitize_filename(word: str) -> str:
    """
    Sanitize a word to create a valid filename
    
    Args:
        word: The word to sanitize
        
    Returns:
        Sanitized filename-safe string
    """
    # Remove or replace invalid filename characters
    # Keep alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', word)
    
    # Replace spaces with underscores (optional, but cleaner for filenames)
    sanitized = sanitized.replace(' ', '_')
    
    # Remove leading/trailing dots and spaces (Windows doesn't like these)
    sanitized = sanitized.strip('. ')
    
    # If empty after sanitization, use a default name
    if not sanitized:
        sanitized = 'word'
    
    # Limit length to avoid filesystem issues
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized


def get_output_path(output_dir: str, word: str, extension: str = '.wav') -> str:
    """
    Generate a valid output path for a word
    
    Args:
        output_dir: Base output directory
        word: The word to generate a filename for
        extension: File extension (default: .wav)
        
    Returns:
        Full path to the output file
    """
    if not output_dir:
        raise ValueError("Output directory cannot be empty")
    
    # Ensure extension starts with dot
    if not extension.startswith('.'):
        extension = '.' + extension
    
    # Sanitize the word for filename
    filename = sanitize_filename(word)
    
    # Construct full path
    output_path = os.path.join(output_dir, filename + extension)
    
    # Handle filename conflicts by appending a number
    base_path = output_path
    counter = 1
    while os.path.exists(output_path):
        name, ext = os.path.splitext(base_path)
        output_path = f"{name}_{counter}{ext}"
        counter += 1
        # Safety limit to avoid infinite loops
        if counter > 1000:
            raise RuntimeError(f"Too many filename conflicts for: {word}")
    
    return output_path


def validate_output_directory(output_dir: str) -> Tuple[bool, str]:
    """
    Validate that an output directory exists and is writable
    
    Args:
        output_dir: Path to the output directory
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not output_dir:
        return False, "Output directory is not specified"
    
    # Check if directory exists
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create output directory: {str(e)}"
    
    # Check if it's actually a directory
    if not os.path.isdir(output_dir):
        return False, f"Path exists but is not a directory: {output_dir}"
    
    # Check if it's writable
    test_file = os.path.join(output_dir, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception as e:
        return False, f"Output directory is not writable: {str(e)}"
    
    return True, ""
