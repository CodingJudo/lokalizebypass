"""Read/write i18n JSON files."""

import json
from pathlib import Path
from typing import Dict, Any


def read_i18n_file(file_path: Path) -> Dict[str, Any]:
    """
    Read a single i18n JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with translation keys and values
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"i18n file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_all_i18n_files(i18n_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Read all JSON files from i18n directory.
    
    Args:
        i18n_dir: Path to directory containing i18n JSON files
        
    Returns:
        Dictionary mapping language codes to their translation dictionaries
        Example: {"sv": {"key1": "value1"}, "en": {"key1": "value1"}}
    """
    if not i18n_dir.exists():
        return {}
    
    result: Dict[str, Dict[str, Any]] = {}
    
    for json_file in i18n_dir.glob("*.json"):
        lang_code = json_file.stem
        try:
            result[lang_code] = read_i18n_file(json_file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Skip invalid files, but could log warning in future
            continue
    
    return result


def write_jsonl(file_path: Path, records: list[Dict[str, Any]]) -> None:
    """
    Write records to a JSONL file (one JSON object per line).
    
    Args:
        file_path: Path to output JSONL file
        records: List of dictionaries to write
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

