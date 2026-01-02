"""Tests for merge-only-missing logic."""

import json
import pytest
from pathlib import Path

from src.merge import merge_translations, write_i18n_file, read_memory_jsonl


def test_merge_translations_updates_missing(tmp_path: Path):
    """Test that merge updates missing translations."""
    # Create memory.jsonl
    memory_file = tmp_path / "memory.jsonl"
    memory_records = [
        {
            "key": "test.key1",
            "ns": "test",
            "source_lang": "sv",
            "source": "Test value 1",
            "targets": {"en": "Test value 1", "de": None},
            "status": {"en": "ok", "de": "missing"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "abc123"
        },
        {
            "key": "test.key2",
            "ns": "test",
            "source_lang": "sv",
            "source": "Test value 2",
            "targets": {"en": "Test value 2", "de": "Test Wert 2"},
            "status": {"en": "ok", "de": "ok"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "def456"
        }
    ]
    
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Create i18n directory with existing en.json (missing test.key2)
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"test.key1": "Existing value"}', encoding="utf-8")
    
    # Merge translations for en
    stats = merge_translations(memory_file, target_lang="en", i18n_dir=i18n_dir, force=False)
    
    # Verify stats
    assert stats["updated"] == 1  # test.key2 was updated
    assert stats["skipped"] == 1  # test.key1 was skipped (already had value)
    
    # Verify file contents (nested structure)
    with open(en_file, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    
    # Data is unflattened, so "test.key1" becomes {"test": {"key1": "..."}}
    assert en_data["test"]["key1"] == "Existing value"  # Not overwritten
    assert en_data["test"]["key2"] == "Test value 2"  # Updated from memory


def test_merge_translations_does_not_overwrite_existing(tmp_path: Path):
    """Test that merge does not overwrite existing non-empty translations."""
    # Create memory.jsonl
    memory_file = tmp_path / "memory.jsonl"
    memory_records = [
        {
            "key": "test.key",
            "ns": "test",
            "source_lang": "sv",
            "source": "Source value",
            "targets": {"en": "New value"},
            "status": {"en": "ok"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "abc123"
        }
    ]
    
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Create i18n directory with existing en.json
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"test.key": "Existing value"}', encoding="utf-8")
    
    # Merge translations for en (without force)
    stats = merge_translations(memory_file, target_lang="en", i18n_dir=i18n_dir, force=False)
    
    # Verify skipped
    assert stats["skipped"] == 1
    assert stats["updated"] == 0
    
    # Verify file contents unchanged (nested structure)
    with open(en_file, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    
    assert en_data["test"]["key"] == "Existing value"  # Not overwritten


def test_merge_translations_force_overwrite(tmp_path: Path):
    """Test that merge overwrites when force=True."""
    # Create memory.jsonl
    memory_file = tmp_path / "memory.jsonl"
    memory_records = [
        {
            "key": "test.key",
            "ns": "test",
            "source_lang": "sv",
            "source": "Source value",
            "targets": {"en": "New value"},
            "status": {"en": "ok"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "abc123"
        }
    ]
    
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Create i18n directory with existing en.json
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    en_file = i18n_dir / "en.json"
    en_file.write_text('{"test.key": "Existing value"}', encoding="utf-8")
    
    # Merge translations for en (with force)
    stats = merge_translations(memory_file, target_lang="en", i18n_dir=i18n_dir, force=True)
    
    # Verify updated
    assert stats["updated"] == 1
    assert stats["skipped"] == 0
    
    # Verify file contents overwritten (nested structure)
    with open(en_file, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    
    assert en_data["test"]["key"] == "New value"  # Overwritten


def test_merge_translations_creates_new_file(tmp_path: Path):
    """Test that merge creates new file if it doesn't exist."""
    # Create memory.jsonl
    memory_file = tmp_path / "memory.jsonl"
    memory_records = [
        {
            "key": "test.key",
            "ns": "test",
            "source_lang": "sv",
            "source": "Source value",
            "targets": {"de": "Neuer Wert"},
            "status": {"de": "ok"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "abc123"
        }
    ]
    
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Create i18n directory (no de.json yet)
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    
    # Merge translations for de
    stats = merge_translations(memory_file, target_lang="de", i18n_dir=i18n_dir, force=False)
    
    # Verify updated
    assert stats["updated"] == 1
    
    # Verify file was created
    de_file = i18n_dir / "de.json"
    assert de_file.exists()
    
    with open(de_file, "r", encoding="utf-8") as f:
        de_data = json.load(f)
    
    # Data is unflattened, so "test.key" becomes {"test": {"key": "..."}}
    assert de_data["test"]["key"] == "Neuer Wert"


def test_merge_translations_skips_missing_values(tmp_path: Path):
    """Test that merge skips keys where memory value is missing."""
    # Create memory.jsonl with missing target value
    memory_file = tmp_path / "memory.jsonl"
    memory_records = [
        {
            "key": "test.key",
            "ns": "test",
            "source_lang": "sv",
            "source": "Source value",
            "targets": {"en": None},
            "status": {"en": "missing"},
            "placeholder_signature": "",
            "meta": {},
            "fingerprint": "abc123"
        }
    ]
    
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Create i18n directory
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    en_file = i18n_dir / "en.json"
    en_file.write_text('{}', encoding="utf-8")
    
    # Merge translations for en
    stats = merge_translations(memory_file, target_lang="en", i18n_dir=i18n_dir, force=False)
    
    # Verify nothing updated
    assert stats["updated"] == 0
    assert stats["skipped"] == 0
    
    # Verify file still empty
    with open(en_file, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    
    assert len(en_data) == 0

