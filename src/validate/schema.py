"""Validate JSON schema for LLM translation output."""

import json
from typing import Dict, Any, List, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_llm_output(response_text: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    Validate LLM translation output against required schema.
    
    Args:
        response_text: Raw text response from LLM
        
    Returns:
        Tuple of (is_valid: bool, parsed_data: dict, error_message: str)
        If valid, parsed_data contains the parsed JSON.
        If invalid, error_message describes the issue.
    """
    # Check 1: Parseable JSON
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        return False, {}, f"Output not parseable JSON: {e}"
    
    # Check 2: Required top-level fields
    if not isinstance(data, dict):
        return False, {}, "Output must be a JSON object"
    
    if "targetLanguage" not in data:
        return False, data, "Missing required field: targetLanguage"
    
    if "translations" not in data:
        return False, data, "Missing required field: translations"
    
    # Check 3: Field types
    if not isinstance(data["targetLanguage"], str):
        return False, data, "targetLanguage must be a string"
    
    if not isinstance(data["translations"], list):
        return False, data, "translations must be an array"
    
    # Check 4: Each translation entry
    for i, translation in enumerate(data["translations"]):
        if not isinstance(translation, dict):
            return False, data, f"translations[{i}] must be an object"
        
        if "key" not in translation:
            return False, data, f"translations[{i}] missing required field: key"
        
        if "text" not in translation:
            return False, data, f"translations[{i}] missing required field: text"
        
        if not isinstance(translation["key"], str):
            return False, data, f"translations[{i}].key must be a string"
        
        if not isinstance(translation["text"], str):
            return False, data, f"translations[{i}].text must be a string"
        
        # Check 5: Empty text (hard fail)
        if translation["text"].strip() == "":
            return False, data, f"translations[{i}].text cannot be empty"
    
    return True, data, ""


def validate_translation_entry(
    source_text: str,
    source_signature: str,
    translated_text: str,
    key: str
) -> Tuple[bool, str]:
    """
    Validate a single translation entry against placeholder signature.
    
    Args:
        source_text: Source translation text
        source_signature: Protected token signature from source
        translated_text: Translated text to validate
        key: Translation key (for error messages)
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    from src.validate.placeholders import protected_signature, validate_protected_tokens
    
    # Validate protected tokens match
    is_valid, diff = validate_protected_tokens(source_text, translated_text)
    
    if not is_valid:
        missing_str = ", ".join(f"{k}:{v}" for k, v in diff["missing"].items())
        extra_str = ", ".join(f"{k}:{v}" for k, v in diff["extra"].items())
        errors = []
        if missing_str:
            errors.append(f"missing tokens: {missing_str}")
        if extra_str:
            errors.append(f"extra tokens: {extra_str}")
        return False, f"Protected token mismatch for key '{key}': {'; '.join(errors)}"
    
    # Verify signature matches
    translated_signature = protected_signature(translated_text)
    if translated_signature != source_signature:
        return False, (
            f"Placeholder signature mismatch for key '{key}': "
            f"expected '{source_signature}', got '{translated_signature}'"
        )
    
    return True, ""

