"""Tests for JSON schema validation."""

import json
import pytest
from pathlib import Path

from src.validate.schema import validate_llm_output, validate_translation_entry, ValidationError


def test_validate_llm_output_valid():
    """Test validation of valid LLM output."""
    response = {
        "targetLanguage": "de",
        "translations": [
            {"key": "booking.confirm", "text": "Buchung bestätigen"}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is True
    assert error_msg == ""
    assert data["targetLanguage"] == "de"
    assert len(data["translations"]) == 1


def test_validate_llm_output_invalid_json():
    """Test validation fails on invalid JSON."""
    response_text = "{ invalid json }"
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "not parseable JSON" in error_msg


def test_validate_llm_output_missing_target_language():
    """Test validation fails when targetLanguage is missing."""
    response = {
        "translations": [
            {"key": "booking.confirm", "text": "Buchung bestätigen"}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "targetLanguage" in error_msg


def test_validate_llm_output_missing_translations():
    """Test validation fails when translations is missing."""
    response = {
        "targetLanguage": "de"
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "translations" in error_msg


def test_validate_llm_output_missing_key():
    """Test validation fails when translation entry is missing key."""
    response = {
        "targetLanguage": "de",
        "translations": [
            {"text": "Buchung bestätigen"}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "key" in error_msg


def test_validate_llm_output_missing_text():
    """Test validation fails when translation entry is missing text."""
    response = {
        "targetLanguage": "de",
        "translations": [
            {"key": "booking.confirm"}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "text" in error_msg


def test_validate_llm_output_empty_text():
    """Test validation fails when translation text is empty."""
    response = {
        "targetLanguage": "de",
        "translations": [
            {"key": "booking.confirm", "text": ""}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "cannot be empty" in error_msg


def test_validate_llm_output_whitespace_only_text():
    """Test validation fails when translation text is only whitespace."""
    response = {
        "targetLanguage": "de",
        "translations": [
            {"key": "booking.confirm", "text": "   "}
        ]
    }
    response_text = json.dumps(response)
    
    is_valid, data, error_msg = validate_llm_output(response_text)
    assert is_valid is False
    assert "cannot be empty" in error_msg


def test_validate_translation_entry_valid():
    """Test validation of translation entry with matching protected tokens."""
    source_text = "Hej {{name}} \\1"
    source_sig = "\\1:1|{{name}}:1"
    translated_text = "Hello {{name}} \\1"
    
    is_valid, error_msg = validate_translation_entry(
        source_text, source_sig, translated_text, "test.key"
    )
    assert is_valid is True
    assert error_msg == ""


def test_validate_translation_entry_missing_token():
    """Test validation fails when protected token is missing."""
    source_text = "Hej {{name}} \\1"
    source_sig = "\\1:1|{{name}}:1"
    translated_text = "Hello {{name}}"
    
    is_valid, error_msg = validate_translation_entry(
        source_text, source_sig, translated_text, "test.key"
    )
    assert is_valid is False
    assert "missing tokens" in error_msg
    assert "\\1" in error_msg


def test_validate_translation_entry_extra_token():
    """Test validation fails when extra protected token is present."""
    source_text = "Hej {{name}}"
    source_sig = "{{name}}:1"
    translated_text = "Hello {{name}} \\1"
    
    is_valid, error_msg = validate_translation_entry(
        source_text, source_sig, translated_text, "test.key"
    )
    assert is_valid is False
    assert "extra tokens" in error_msg
    assert "\\1" in error_msg


def test_validate_translation_entry_token_count_mismatch():
    """Test validation fails when token count doesn't match."""
    source_text = "Repeat \\1 \\1"
    source_sig = "\\1:2"
    translated_text = "Repeat \\1"
    
    is_valid, error_msg = validate_translation_entry(
        source_text, source_sig, translated_text, "test.key"
    )
    assert is_valid is False
    assert "missing tokens" in error_msg


def test_validate_translation_entry_signature_mismatch():
    """Test validation fails when signature doesn't match (different token counts)."""
    # Use a case where tokens match but signature was computed incorrectly
    source_text = "Hej {{name}}"
    # Wrong signature (should be "{{name}}:1" but we pass wrong one)
    source_sig = "{{name}}:2"  # Wrong count
    translated_text = "Hello {{name}}"
    
    is_valid, error_msg = validate_translation_entry(
        source_text, source_sig, translated_text, "test.key"
    )
    # Should fail because signature doesn't match (even though tokens are correct)
    assert is_valid is False
    assert "signature mismatch" in error_msg.lower() or "signature" in error_msg.lower()

