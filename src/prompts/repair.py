"""Repair prompt for fixing invalid JSON responses."""


def build_repair_prompt(
    invalid_response: str,
    original_prompt: str,
    error_message: str
) -> str:
    """
    Build a repair prompt to fix invalid JSON responses.
    
    Args:
        invalid_response: The invalid JSON response from the LLM
        original_prompt: The original translation prompt
        error_message: Description of the validation error
    
    Returns:
        Repair prompt string
    """
    prompt = f"""The previous translation response was invalid. Please fix it.

ERROR: {error_message}

INVALID RESPONSE:
{invalid_response}

ORIGINAL REQUEST:
{original_prompt}

Please provide a corrected JSON response that:
1. Is valid JSON (parseable)
2. Contains all required fields: targetLanguage, translations (array)
3. Each translation has "key" and "text" fields
4. All text fields are non-empty strings
5. Preserves placeholders exactly as in source

Return ONLY the corrected JSON, no markdown, no commentary.
"""
    return prompt

