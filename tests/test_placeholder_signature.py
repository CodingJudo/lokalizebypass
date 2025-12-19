"""Tests for placeholder signature generation."""

import pytest
from collections import Counter

from src.validate.placeholders import (
    extract_placeholders,
    generate_placeholder_signature,
    extract_protected_tokens,
    protected_signature,
    validate_protected_tokens,
)


def test_extract_placeholders_icu_simple():
    """Test extraction of simple ICU placeholders."""
    placeholders = extract_placeholders("Hello {name}!")
    assert "{name}" in placeholders


def test_extract_placeholders_icu_complex():
    """Test extraction of complex ICU placeholders."""
    placeholders = extract_placeholders("You have {count, plural, one {# message} other {# messages}}")
    assert len(placeholders) >= 1
    assert any("{count" in p for p in placeholders)


def test_extract_placeholders_double_brace():
    """Test extraction of double brace placeholders."""
    placeholders = extract_placeholders("Value: {{value}}")
    assert "{{value}}" in placeholders


def test_extract_placeholders_printf():
    """Test extraction of printf-style placeholders."""
    placeholders = extract_placeholders("Percent: %s")
    assert "%s" in placeholders
    
    placeholders = extract_placeholders("Number: %d")
    assert "%d" in placeholders


def test_extract_placeholders_multiple():
    """Test extraction of multiple placeholder types."""
    placeholders = extract_placeholders("Hello {name}, you have %s messages")
    assert "{name}" in placeholders
    assert "%s" in placeholders


def test_extract_placeholders_none():
    """Test that strings without placeholders return empty set."""
    placeholders = extract_placeholders("Hello world")
    assert len(placeholders) == 0
    
    placeholders = extract_placeholders("")
    assert len(placeholders) == 0


def test_generate_placeholder_signature_simple():
    """Test signature generation for simple placeholder."""
    sig = generate_placeholder_signature("Hello {name}!")
    assert "ICU" in sig
    assert "{name}" in sig


def test_generate_placeholder_signature_printf():
    """Test signature generation for printf placeholder."""
    sig = generate_placeholder_signature("Percent: %s")
    assert "%s" in sig


def test_generate_placeholder_signature_double_brace():
    """Test signature generation for double brace placeholder."""
    sig = generate_placeholder_signature("Value: {{value}}")
    assert "{{value}}" in sig


def test_generate_placeholder_signature_multiple():
    """Test signature generation for multiple placeholder types."""
    sig = generate_placeholder_signature("Hello {name}, you have %s messages")
    assert "ICU" in sig
    assert "{name}" in sig
    assert "%s" in sig


def test_generate_placeholder_signature_empty():
    """Test signature generation for string without placeholders."""
    sig = generate_placeholder_signature("Hello world")
    assert sig == ""
    
    sig = generate_placeholder_signature("")
    assert sig == ""


def test_generate_placeholder_signature_deterministic():
    """Test that signature generation is deterministic."""
    text = "Hello {name}, you have %s messages"
    sig1 = generate_placeholder_signature(text)
    sig2 = generate_placeholder_signature(text)
    assert sig1 == sig2


def test_generate_placeholder_signature_order_independent():
    """Test that signature handles placeholders in different orders consistently."""
    # Same placeholders, different order in text
    text1 = "Hello {name}, count: {count}"
    text2 = "Count: {count}, hello {name}"
    
    sig1 = generate_placeholder_signature(text1)
    sig2 = generate_placeholder_signature(text2)
    
    # Signatures should be the same (sorted)
    assert sig1 == sig2


# Protected token tests

def test_extract_protected_tokens_double_curly():
    """Test extraction of double-curly protected tokens."""
    tokens = extract_protected_tokens("Hej {{name}}")
    assert tokens == Counter({"{{name}}": 1})


def test_extract_protected_tokens_backslash_number():
    """Test extraction of backslash-number protected tokens."""
    tokens = extract_protected_tokens("Value \\1 and \\2")
    assert tokens == Counter({"\\1": 1, "\\2": 1})


def test_extract_protected_tokens_repeat():
    """Test extraction of repeated protected tokens."""
    tokens = extract_protected_tokens("Repeat \\1 \\1")
    assert tokens == Counter({"\\1": 2})


def test_extract_protected_tokens_mixed():
    """Test extraction of mixed protected tokens."""
    tokens = extract_protected_tokens("Hej {{name}} \\1")
    assert tokens == Counter({"{{name}}": 1, "\\1": 1})


def test_extract_protected_tokens_none():
    """Test extraction when no protected tokens exist."""
    tokens = extract_protected_tokens("Hello world")
    assert tokens == Counter()
    
    tokens = extract_protected_tokens("")
    assert tokens == Counter()


def test_extract_protected_tokens_double_curly_non_greedy():
    """Test that double-curly extraction is non-greedy."""
    tokens = extract_protected_tokens("{{first}} and {{second}}")
    assert tokens == Counter({"{{first}}": 1, "{{second}}": 1})


def test_protected_signature_simple():
    """Test protected signature generation for simple case."""
    sig = protected_signature("Hej {{name}}")
    assert sig == "{{name}}:1"


def test_protected_signature_backslash():
    """Test protected signature generation with backslash-number."""
    sig = protected_signature("Value \\1")
    assert sig == "\\1:1"


def test_protected_signature_mixed():
    """Test protected signature generation with mixed tokens."""
    sig = protected_signature("Hej {{name}} \\1")
    # Should be lexicographically sorted: \\1 comes before {{name}} (backslash < curly brace)
    assert sig == "\\1:1|{{name}}:1"


def test_protected_signature_repeat():
    """Test protected signature generation with repeated tokens."""
    sig = protected_signature("Repeat \\1 \\1")
    assert sig == "\\1:2"


def test_protected_signature_empty():
    """Test protected signature generation for empty string."""
    sig = protected_signature("Hello world")
    assert sig == ""
    
    sig = protected_signature("")
    assert sig == ""


def test_protected_signature_deterministic():
    """Test that protected signature generation is deterministic."""
    text = "Hej {{name}} \\1"
    sig1 = protected_signature(text)
    sig2 = protected_signature(text)
    assert sig1 == sig2


def test_protected_signature_order_independent():
    """Test that protected signature handles tokens in different orders consistently."""
    text1 = "{{first}} \\1 {{second}}"
    text2 = "{{second}} \\1 {{first}}"
    
    sig1 = protected_signature(text1)
    sig2 = protected_signature(text2)
    
    # Signatures should be the same (sorted lexicographically)
    assert sig1 == sig2


def test_validate_protected_tokens_valid():
    """Test validation when tokens match exactly."""
    is_valid, diff = validate_protected_tokens("Hej {{name}} \\1", "Hello {{name}} \\1")
    assert is_valid is True
    assert diff["missing"] == {}
    assert diff["extra"] == {}


def test_validate_protected_tokens_missing():
    """Test validation when tokens are missing."""
    is_valid, diff = validate_protected_tokens("Hej {{name}} \\1", "Hello")
    assert is_valid is False
    assert "{{name}}" in diff["missing"] or "\\1" in diff["missing"]


def test_validate_protected_tokens_extra():
    """Test validation when extra tokens are present."""
    is_valid, diff = validate_protected_tokens("Hej {{name}}", "Hello {{name}} \\1")
    assert is_valid is False
    assert "\\1" in diff["extra"]


def test_validate_protected_tokens_count_mismatch():
    """Test validation when token counts don't match."""
    is_valid, diff = validate_protected_tokens("Repeat \\1 \\1", "Repeat \\1")
    assert is_valid is False
    assert diff["missing"]["\\1"] == 1

