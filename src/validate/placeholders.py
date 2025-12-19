"""Detect and validate placeholders in translation strings."""

import re
from typing import Set
from collections import Counter


def extract_placeholders(text: str) -> Set[str]:
    """
    Extract all placeholders from a translation string.
    
    Supports multiple placeholder formats:
    - {name}, {name:format} (ICU-style)
    - {{name}} (double braces)
    - %s, %d, %f (printf-style)
    - {0}, {1} (positional)
    
    Args:
        text: Translation string to analyze
        
    Returns:
        Set of placeholder strings found (e.g., {"{name}", "%s"})
    """
    placeholders: Set[str] = set()
    
    if not text:
        return placeholders
    
    # Extract double braces first ({{name}}) to avoid matching inner braces
    # Double braces: {{name}}
    double_brace_pattern = r'\{\{[^}]+\}\}'
    double_brace_matches = list(re.finditer(double_brace_pattern, text))
    for match in double_brace_matches:
        placeholders.add(match.group(0))
    
    # Remove double brace matches from text before extracting ICU placeholders
    # to avoid double-counting
    text_without_double_braces = text
    for match in reversed(double_brace_matches):  # Reverse to maintain positions
        text_without_double_braces = (
            text_without_double_braces[:match.start()] + 
            " " * (match.end() - match.start()) + 
            text_without_double_braces[match.end():]
        )
    
    # ICU-style placeholders: {name} or {name, type, format}
    # Matches: {name}, {name:format}, {count, plural, ...}
    icu_pattern = r'\{[^}]+\}'
    for match in re.finditer(icu_pattern, text_without_double_braces):
        placeholders.add(match.group(0))
    
    # printf-style: %s, %d, %f, %.*s, etc.
    printf_pattern = r'%[sdifxXo]|%\.\*[sdifxXo]|%[0-9]+[sdifxXo]'
    for match in re.finditer(printf_pattern, text):
        placeholders.add(match.group(0))
    
    return placeholders


def generate_placeholder_signature(text: str) -> str:
    """
    Generate a stable signature representing placeholders in a string.
    
    The signature is deterministic and can be used to compare placeholder
    patterns between source and target translations.
    
    Args:
        text: Translation string to analyze
        
    Returns:
        Placeholder signature string, e.g., "{ } / %s" or "ICU {name, plural}"
    """
    placeholders = extract_placeholders(text)
    
    if not placeholders:
        return ""
    
    # Sort for deterministic output
    sorted_placeholders = sorted(placeholders)
    
    # Group by type for readability
    icu_placeholders = [p for p in sorted_placeholders if p.startswith("{") and not p.startswith("{{")]
    double_brace = [p for p in sorted_placeholders if p.startswith("{{")]
    printf_placeholders = [p for p in sorted_placeholders if p.startswith("%")]
    
    parts = []
    if icu_placeholders:
        parts.append("ICU " + " ".join(icu_placeholders))
    if double_brace:
        parts.append(" ".join(double_brace))
    if printf_placeholders:
        parts.append("/".join(printf_placeholders))
    
    return " / ".join(parts)


def extract_protected_tokens(text: str) -> Counter[str]:
    """
    Extract protected tokens from a translation string (Lokalise format).
    
    Protected tokens MUST NOT be translated and MUST be preserved exactly.
    Supports:
    - Double-curly variables: {{...}} (non-greedy)
    - Backslash-number references: \\1, \\2, \\10, etc.
    
    Args:
        text: Translation string to analyze
        
    Returns:
        Counter mapping token strings to their counts
        Example: Counter({"{{name}}": 1, "\\1": 2})
    """
    tokens = Counter()
    
    if not text:
        return tokens
    
    # Double-curly variables: {{...}} (non-greedy)
    double_curly_pattern = r'\{\{.*?\}\}'
    for match in re.finditer(double_curly_pattern, text):
        tokens[match.group(0)] += 1
    
    # Backslash-number references: \1, \2, \10, etc.
    # In the string literal, this is written as "\\1" but represents "\1"
    backslash_number_pattern = r'\\\d+'
    for match in re.finditer(backslash_number_pattern, text):
        tokens[match.group(0)] += 1
    
    return tokens


def protected_signature(text: str) -> str:
    """
    Generate a deterministic signature for protected tokens.
    
    The signature is a sorted, deterministic representation of all protected
    tokens and their counts, suitable for comparison between source and target.
    
    Args:
        text: Translation string to analyze
        
    Returns:
        Signature string with format "TOKEN:COUNT|TOKEN:COUNT" (sorted lexicographically)
        Example: "{{name}}:1|\\1:2"
    """
    tokens = extract_protected_tokens(text)
    
    if not tokens:
        return ""
    
    # Sort tokens lexicographically for deterministic output
    sorted_items = sorted(tokens.items())
    
    # Format as "TOKEN:COUNT" pairs joined by "|"
    parts = [f"{token}:{count}" for token, count in sorted_items]
    return "|".join(parts)


def validate_protected_tokens(source_text: str, translated_text: str) -> tuple[bool, dict]:
    """
    Validate that protected tokens are preserved exactly in translation.
    
    Compares the protected token counts between source and translated text.
    
    Args:
        source_text: Source translation string
        translated_text: Translated string to validate
        
    Returns:
        Tuple of (is_valid: bool, diff: dict)
        diff contains:
        - "source": Counter of source tokens
        - "translated": Counter of translated tokens
        - "missing": Counter of tokens in source but not in translated (or with lower count)
        - "extra": Counter of tokens in translated but not in source (or with higher count)
    """
    source_tokens = extract_protected_tokens(source_text)
    translated_tokens = extract_protected_tokens(translated_text)
    
    # Compute differences
    missing = source_tokens - translated_tokens
    extra = translated_tokens - source_tokens
    
    is_valid = len(missing) == 0 and len(extra) == 0
    
    diff = {
        "source": dict(source_tokens),
        "translated": dict(translated_tokens),
        "missing": dict(missing),
        "extra": dict(extra),
    }
    
    return is_valid, diff


# TODO: Phase 3+ - Translation validation hook
# During translate-missing phase, the program MUST run validate_protected_tokens()
# for each translated string and hard-fail if mismatch is detected.
# Example usage:
#   is_valid, diff = validate_protected_tokens(source_sv, translated_text)
#   if not is_valid:
#       raise ValidationError(f"Protected tokens mismatch: {diff}")
# This ensures protected tokens are never translated or modified.

