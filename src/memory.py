"""Build/update canonical memory artifact."""

import hashlib
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

from src.io_json import read_all_i18n_files, read_i18n_files_explicit
from src.validate.placeholders import protected_signature


def extract_namespace(key: str) -> str:
    """
    Extract namespace from a translation key.
    
    Namespace is the part before the first dot, or "default" if no dot.
    
    Args:
        key: Translation key (e.g., "booking.confirm" or "welcome")
        
    Returns:
        Namespace string (e.g., "booking" or "default")
    """
    if "." in key:
        return key.split(".", 1)[0]
    return "default"


def is_missing(value: Any) -> bool:
    """
    Check if a translation value is considered missing.
    
    Args:
        value: Translation value to check
        
    Returns:
        True if value is None, empty string, or empty dict
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def compute_fingerprint(key: str, source: str, placeholder_signature: str, context_version: str = "1.0") -> str:
    """
    Compute a stable fingerprint for a translation entry.
    
    Used to detect when source translations change (needs_review).
    
    Args:
        key: Translation key
        source: Source translation text
        placeholder_signature: Placeholder signature
        context_version: Version string for fingerprint context
        
    Returns:
        SHA256 hash as hex string
    """
    content = f"{key}|{source}|{placeholder_signature}|{context_version}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_memory(
    output_file: Path,
    source_lang: str = "sv",
    i18n_dir: Optional[Path] = None,
    i18n_files: Optional[Dict[str, Path]] = None
) -> None:
    """
    Build memory.jsonl from i18n JSON files.
    
    Reads i18n files either from a directory or from explicit file paths,
    identifies missing translations, generates placeholder signatures, and writes memory.jsonl.
    
    Args:
        output_file: Path to output memory.jsonl file
        source_lang: Source language code (default: "sv")
        i18n_dir: Directory containing i18n JSON files (folder mode)
        i18n_files: Dictionary mapping language codes to file paths (file mode)
                   Example: {"en": Path("en.json"), "fr": Path("fr.json")}
    
    Raises:
        ValueError: If neither i18n_dir nor i18n_files is provided, or if both are provided
        ValueError: If source language is not found in i18n files
    """
    # Validate that exactly one mode is specified
    if i18n_dir is None and i18n_files is None:
        raise ValueError("Either i18n_dir or i18n_files must be provided")
    if i18n_dir is not None and i18n_files is not None:
        raise ValueError("Cannot specify both i18n_dir and i18n_files")
    
    # Read i18n files based on mode
    if i18n_dir is not None:
        # Folder mode: read all JSON files from directory
        i18n_data = read_all_i18n_files(i18n_dir)
    else:
        # File mode: read explicit files
        file_paths = list(i18n_files.values())
        i18n_data = read_i18n_files_explicit(file_paths, lang_map=i18n_files)
    
    if source_lang not in i18n_data:
        raise ValueError(f"Source language '{source_lang}' not found in i18n files")
    
    source_data = i18n_data[source_lang]
    
    # Collect all unique keys from all languages
    all_keys: Set[str] = set(source_data.keys())
    for lang_data in i18n_data.values():
        all_keys.update(lang_data.keys())
    
    # Build memory records
    records: List[Dict[str, Any]] = []
    
    for key in sorted(all_keys):  # Deterministic ordering
        source_value = source_data.get(key)
        
        # Skip keys that don't exist in source
        if key not in source_data:
            continue
        
        # Convert source value to string if it's not already
        source_text = str(source_value) if source_value is not None else ""
        
        # Generate placeholder signature from source (using protected tokens)
        placeholder_sig = protected_signature(source_text)
        
        # Build targets and status dictionaries
        targets: Dict[str, Any] = {}
        status: Dict[str, str] = {}
        
        for lang_code in sorted(i18n_data.keys()):  # Deterministic ordering
            if lang_code == source_lang:
                continue
            
            lang_value = i18n_data[lang_code].get(key)
            targets[lang_code] = lang_value
            
            if is_missing(lang_value):
                status[lang_code] = "missing"
            else:
                status[lang_code] = "ok"
        
        # Compute fingerprint
        fingerprint = compute_fingerprint(key, source_text, placeholder_sig)
        
        # Build record
        record: Dict[str, Any] = {
            "key": key,
            "ns": extract_namespace(key),
            "source_lang": source_lang,
            "source": source_text,
            "targets": targets,
            "status": status,
            "placeholder_signature": placeholder_sig,
            "meta": {},  # Can be populated later
            "fingerprint": fingerprint,
        }
        
        records.append(record)
    
    # Write JSONL file
    from src.io_json import write_jsonl
    write_jsonl(output_file, records)

