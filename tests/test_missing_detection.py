"""Tests for missing detection."""

import pytest
from pathlib import Path

from src.memory import is_missing, build_memory
from src.io_json import read_i18n_file


def test_is_missing_none():
    """Test that None is considered missing."""
    assert is_missing(None) is True


def test_is_missing_empty_string():
    """Test that empty string is considered missing."""
    assert is_missing("") is True
    assert is_missing("   ") is True  # Whitespace only


def test_is_missing_empty_dict():
    """Test that empty dict is considered missing."""
    assert is_missing({}) is True


def test_is_missing_not_missing():
    """Test that non-empty values are not missing."""
    assert is_missing("Hello") is False
    assert is_missing("  Hello  ") is False
    assert is_missing({"key": "value"}) is False
    assert is_missing(0) is False
    assert is_missing(False) is False


def test_build_memory_missing_detection(tmp_path: Path):
    """Test that build_memory correctly identifies missing translations."""
    # Create test i18n files
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    
    # Source language (sv) - complete
    sv_file = i18n_dir / "sv.json"
    sv_file.write_text('{"key1": "Värde 1", "key2": "Värde 2"}', encoding="utf-8")
    
    # Target language (en) - partial
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"key1": "Value 1", "key2": null}', encoding="utf-8")
    
    # Another target (de) - empty
    de_file = i18n_dir / "de.json"
    de_file.write_text('{"key1": "", "key2": null}', encoding="utf-8")
    
    # Build memory
    output_file = tmp_path / "memory.jsonl"
    build_memory(i18n_dir, output_file, source_lang="sv")
    
    # Read and verify
    import json
    records = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    
    assert len(records) == 2
    
    # Check key1
    key1_record = next(r for r in records if r["key"] == "key1")
    assert key1_record["status"]["en"] == "ok"  # Has value
    assert key1_record["status"]["de"] == "missing"  # Empty string
    
    # Check key2
    key2_record = next(r for r in records if r["key"] == "key2")
    assert key2_record["status"]["en"] == "missing"  # null
    assert key2_record["status"]["de"] == "missing"  # null

