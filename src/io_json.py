"""Read/write i18n JSON files."""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def flatten_json(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Flatten a nested JSON dictionary into dot-notation keys.
    
    Args:
        data: Nested dictionary to flatten
        parent_key: Parent key prefix (used in recursion)
        sep: Separator for keys (default: ".")
        
    Returns:
        Flattened dictionary with dot-notation keys
        
    Example:
        {"a": {"b": "value"}} -> {"a.b": "value"}
    """
    items = []
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            items.extend(flatten_json(value, new_key, sep=sep).items())
        else:
            # Leaf value (string, number, null, array, etc.)
            items.append((new_key, value))
    
    return dict(items)


def unflatten_json(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    """
    Unflatten a dictionary with dot-notation keys into nested structure.
    
    Args:
        data: Flattened dictionary with dot-notation keys
        sep: Separator used in keys (default: ".")
        
    Returns:
        Nested dictionary structure
        
    Example:
        {"a.b": "value"} -> {"a": {"b": "value"}}
    """
    result = {}
    
    for key, value in data.items():
        parts = key.split(sep)
        current = result
        
        # Navigate/create nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
    
    return result


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
    Read all JSON files from i18n directory and flatten them.
    
    Args:
        i18n_dir: Path to directory containing i18n JSON files
        
    Returns:
        Dictionary mapping language codes to their flattened translation dictionaries
        Example: {"sv": {"key1": "value1", "app.title": "value2"}, ...}
    """
    if not i18n_dir.exists():
        return {}
    
    result: Dict[str, Dict[str, Any]] = {}
    
    for json_file in i18n_dir.glob("*.json"):
        lang_code = json_file.stem
        try:
            nested_data = read_i18n_file(json_file)
            # Flatten the nested structure
            result[lang_code] = flatten_json(nested_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Skip invalid files, but could log warning in future
            continue
    
    return result


def read_i18n_files_explicit(
    file_paths: list[Path],
    lang_map: Optional[Dict[Path, str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Read explicit i18n JSON files and flatten them.
    
    Args:
        file_paths: List of paths to JSON files
        lang_map: Optional mapping from file path to language code.
                  If not provided, language code is inferred from filename stem.
    
    Returns:
        Dictionary mapping language codes to their flattened translation dictionaries
        Example: {"en": {"key1": "value1", "app.title": "value2"}, ...}
    
    Raises:
        FileNotFoundError: If any file doesn't exist
        json.JSONDecodeError: If any file is not valid JSON
    """
    result: Dict[str, Dict[str, Any]] = {}
    
    for file_path in file_paths:
        # Determine language code
        if lang_map and file_path in lang_map:
            lang_code = lang_map[file_path]
        else:
            # Infer from filename stem (e.g., "en.json" -> "en")
            lang_code = file_path.stem
        
        try:
            nested_data = read_i18n_file(file_path)
            # Flatten the nested structure
            result[lang_code] = flatten_json(nested_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Re-raise with context
            raise FileNotFoundError(f"Failed to read i18n file {file_path}: {e}") from e
    
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

