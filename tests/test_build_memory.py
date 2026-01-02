"""Tests for build-memory command and memory artifact generation."""

import json
import pytest
from pathlib import Path

from src.memory import build_memory


def test_build_memory_includes_protected_token_signature(tmp_path: Path):
    """Test that build-memory includes protected token signature in memory.jsonl."""
    # Create test i18n files
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    
    # Source language (sv) with protected tokens
    sv_file = i18n_dir / "sv.json"
    sv_data = {"greeting": "Hej {{name}} \\1", "message": "Du har {count} meddelanden"}
    sv_file.write_text(json.dumps(sv_data, ensure_ascii=False), encoding="utf-8")
    
    # Target language (en) - partial
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"greeting": null, "message": "You have {count} messages"}', encoding="utf-8")
    
    # Build memory
    output_file = tmp_path / "memory.jsonl"
    build_memory(output_file=output_file, source_lang="sv", i18n_dir=i18n_dir)
    
    # Read and verify
    records = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    
    assert len(records) == 2
    
    # Check greeting record has protected token signature
    greeting_record = next(r for r in records if r["key"] == "greeting")
    assert "placeholder_signature" in greeting_record
    # Should contain both {{name}} and \1 tokens
    sig = greeting_record["placeholder_signature"]
    assert "{{name}}" in sig
    assert "\\1" in sig
    
    # Check message record (no protected tokens, but has ICU placeholder)
    message_record = next(r for r in records if r["key"] == "message")
    assert "placeholder_signature" in message_record
    # This one should be empty since we're now using protected_signature only
    # (ICU placeholders are not protected tokens)
    assert message_record["placeholder_signature"] == ""


def test_build_memory_deterministic_ordering(tmp_path: Path):
    """Test that build-memory produces deterministic key ordering."""
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    
    sv_file = i18n_dir / "sv.json"
    sv_file.write_text(
        '{"zebra": "Zebra", "apple": "Apple", "banana": "Banana"}',
        encoding="utf-8"
    )
    
    output_file = tmp_path / "memory.jsonl"
    build_memory(output_file=output_file, source_lang="sv", i18n_dir=i18n_dir)
    
    # Read records
    records = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    
    # Verify keys are sorted
    keys = [r["key"] for r in records]
    assert keys == sorted(keys)
    assert keys == ["apple", "banana", "zebra"]


def test_build_memory_all_required_fields(tmp_path: Path):
    """Test that build-memory includes all required fields."""
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    
    sv_file = i18n_dir / "sv.json"
    sv_file.write_text('{"test.key": "Test value"}', encoding="utf-8")
    
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"test.key": "Test value"}', encoding="utf-8")
    
    output_file = tmp_path / "memory.jsonl"
    build_memory(output_file=output_file, source_lang="sv", i18n_dir=i18n_dir)
    
    # Read record
    with open(output_file, "r", encoding="utf-8") as f:
        record = json.loads(f.readline())
    
    # Verify all required fields are present
    required_fields = [
        "key", "ns", "source_lang", "source", "targets",
        "status", "placeholder_signature", "fingerprint", "meta"
    ]
    for field in required_fields:
        assert field in record, f"Missing required field: {field}"
    
    # Verify field values
    assert record["key"] == "test.key"
    assert record["ns"] == "test"
    assert record["source_lang"] == "sv"
    assert record["source"] == "Test value"
    assert "en" in record["targets"]
    assert "en" in record["status"]
    assert isinstance(record["placeholder_signature"], str)
    assert isinstance(record["fingerprint"], str)
    assert isinstance(record["meta"], dict)

