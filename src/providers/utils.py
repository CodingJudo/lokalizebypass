"""Shared utilities for translation providers."""

import json
import re


def extract_json_from_response(text: str) -> str:
    """
    Extract JSON from LLM response, handling markdown code blocks and commentary.
    
    This function attempts to extract valid JSON from various response formats:
    - Plain JSON strings
    - JSON wrapped in markdown code blocks (```json ... ```)
    - JSON embedded in text with commentary
    
    Args:
        text: Raw response text from LLM
    
    Returns:
        Extracted JSON string (or original text if no valid JSON found)
    """
    # Try to parse as-is first
    try:
        json.loads(text.strip())
        return text.strip()
    except:
        pass
    
    # Try to extract JSON from markdown code blocks
    # Pattern: ```json ... ``` or ``` ... ```
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            json.loads(match.strip())
            return match.strip()
        except:
            pass
    
    # Try to find JSON object in the text
    # Look for { ... } that might be valid JSON
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            json.loads(match.strip())
            return match.strip()
        except:
            pass
    
    # If nothing found, return original (will fail validation)
    return text.strip()


def fix_json_escaping(text: str) -> str:
    """
    Fix common JSON escaping issues with protected tokens.
    
    Attempts to fix cases where backslash-number tokens (\1, \2, etc.)
    are not properly escaped in JSON strings. In JSON, backslashes must be
    escaped, so \1 should be written as \\1.
    
    Also handles control characters (like \x01) that result from unescaped \1.
    Excludes common escape sequences like \n, \t, etc.
    
    Args:
        text: Raw response text from LLM
    
    Returns:
        Potentially fixed text
    """
    # Only fix backslash-number tokens in "text" field values
    # Don't touch the JSON structure itself (newlines, etc.)
    def fix_text_field(match):
        field_start = match.group(1)  # "text": "
        string_content = match.group(2)  # content between quotes
        field_end = match.group(3)  # closing quote
        
        # Fix unescaped backslash-number patterns (\1, \2, etc.)
        # Replace \1, \2, etc. with \\1, \\2, etc.
        # But avoid double-escaping (don't replace \\1)
        # Also avoid common escape sequences like \n, \t, \r
        fixed_content = re.sub(r'(?<!\\)\\([0-9]+)', r'\\\\\1', string_content)
        
        # Also fix control characters that might result from unescaped \1, \2, etc.
        # But exclude common ones: \n (10), \t (9), \r (13)
        def fix_control_char(match_char):
            char_code = ord(match_char.group(0))
            # Control characters: 1-8, 11-12, 14-31 (excluding 9, 10, 13)
            if (1 <= char_code <= 8) or (11 <= char_code <= 12) or (14 <= char_code <= 31):
                return f'\\\\{char_code}'
            return match_char.group(0)
        
        fixed_content = re.sub(r'[\x01-\x08\x0B-\x0C\x0E-\x1F]', fix_control_char, fixed_content)
        return f'{field_start}{fixed_content}{field_end}'
    
    # Pattern to match "text": "..." fields
    pattern = r'("text"\s*:\s*")(.*?)(")'
    fixed = re.sub(pattern, fix_text_field, text, flags=re.DOTALL)
    return fixed

