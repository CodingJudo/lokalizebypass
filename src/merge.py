"""Merge translation results back into per-language i18n JSON files."""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from src.io_json import read_i18n_file, read_all_i18n_files
from src.memory import is_missing


def write_i18n_file(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Write i18n data to a JSON file with proper formatting.
    
    Args:
        file_path: Path to output JSON file
        data: Dictionary of translation keys and values
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_translations(
    memory_file: Path,
    i18n_dir: Path,
    target_lang: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Merge translations from memory.jsonl into target language i18n file.
    
    Only updates keys where the existing value is missing (unless force=True).
    
    Args:
        memory_file: Path to memory.jsonl file
        i18n_dir: Directory containing i18n JSON files
        target_lang: Target language code to merge into
        force: If True, overwrite existing non-empty translations
        
    Returns:
        Dictionary with merge statistics:
        {
            "updated": int,  # Number of keys updated
            "skipped": int,  # Number of keys skipped (already had value)
            "errors": list[str]  # List of error messages
        }
    """
    # Read memory.jsonl
    memory_records: Dict[str, Dict[str, Any]] = {}
    with open(memory_file, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            memory_records[record["key"]] = record
    
    # Read existing i18n file for target language
    target_file = i18n_dir / f"{target_lang}.json"
    if target_file.exists():
        existing_data = read_i18n_file(target_file)
    else:
        existing_data = {}
    
    # Merge translations
    updated = 0
    skipped = 0
    errors = []
    
    for key, record in memory_records.items():
        # Get translation value for target language
        if target_lang not in record.get("targets", {}):
            continue
        
        new_value = record["targets"][target_lang]
        
        # Skip if new value is missing
        if is_missing(new_value):
            continue
        
        # Check if key already exists
        if key in existing_data:
            existing_value = existing_data[key]
            
            # Skip if existing value is not missing and force=False
            if not force and not is_missing(existing_value):
                skipped += 1
                continue
        
        # Update the value
        existing_data[key] = new_value
        updated += 1
    
    # Write updated file
    write_i18n_file(target_file, existing_data)
    
    return {
        "updated": updated,
        "skipped": skipped,
        "errors": errors
    }


def read_memory_jsonl(memory_file: Path) -> list[Dict[str, Any]]:
    """
    Read all records from memory.jsonl.
    
    Args:
        memory_file: Path to memory.jsonl file
        
    Returns:
        List of memory records
    """
    records = []
    if not memory_file.exists():
        return records
    
    with open(memory_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    return records

