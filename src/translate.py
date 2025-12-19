"""Translate missing keys using LLM providers."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.providers.base import TranslationProvider
from src.select import get_missing_keys, batch_by_namespace
from src.memory import is_missing
from src.validate.schema import validate_llm_output, validate_translation_entry
from src.run_logging import RunLogger
from src.merge import read_memory_jsonl


def translate_missing(
    memory_file: Path,
    target_lang: str,
    source_lang: str,
    provider: TranslationProvider,
    logger: Optional[RunLogger] = None,
    batch_size: int = 10,
    max_repairs: int = 2
) -> Dict[str, Any]:
    """
    Translate missing keys for a target language.
    
    Args:
        memory_file: Path to memory.jsonl file
        target_lang: Target language code
        source_lang: Source language code (default: "sv")
        provider: Translation provider instance
        logger: Optional run logger
        batch_size: Maximum items per batch
        max_repairs: Maximum repair attempts per batch
        global_context: Optional global context string for all translations
    
    Returns:
        Dictionary with statistics:
        {
            "batches_processed": int,
            "items_translated": int,
            "items_failed": int,
            "validation_errors": int,
            "repair_attempts": int,
            "updated_records": int
        }
    """
    # Read memory records
    memory_records = read_memory_jsonl(memory_file)
    
    # Get missing keys
    missing_items = get_missing_keys(memory_records, target_lang)
    
    if not missing_items:
        return {
            "batches_processed": 0,
            "items_translated": 0,
            "items_failed": 0,
            "validation_errors": 0,
            "repair_attempts": 0,
            "updated_records": 0
        }
    
    # Create batches
    batches = batch_by_namespace(missing_items, batch_size=batch_size)
    
    # Statistics
    stats = {
        "batches_processed": 0,
        "items_translated": 0,
        "items_failed": 0,
        "validation_errors": 0,
        "repair_attempts": 0,
        "updated_records": 0
    }
    
    # Create memory records lookup (by key)
    memory_lookup = {r["key"]: r for r in memory_records}
    
    # Process each batch
    for batch_id, batch in enumerate(batches, 1):
        if logger:
            logger.log_request(batch_id, source_lang, target_lang, batch)
        
        try:
            # Extract per-key context from memory records
            per_key_context = {}
            for item in batch:
                key = item["key"]
                if key in memory_lookup:
                    meta = memory_lookup[key].get("meta", {})
                    if meta:
                        per_key_context[key] = meta
            
            # Translate batch
            # Note: max_repairs is handled internally by OllamaProvider
            response = provider.translate_batch(
                source_lang=source_lang,
                target_lang=target_lang,
                items=batch,
                global_context=global_context,
                per_key_context=per_key_context if per_key_context else None
            )
            
            if logger:
                logger.log_response(batch_id, response, success=True)
            
            # Response is already validated by provider, but double-check
            # (provider returns dict, not JSON string)
            if not isinstance(response, dict) or "translations" not in response:
                stats["validation_errors"] += 1
                if logger:
                    logger.log_failure(batch_id, "validation_error", "Invalid response format")
                continue
            
            # Update memory records with translations
            for translation in response.get("translations", []):
                key = translation.get("key")
                text = translation.get("text")
                
                if not key or not text:
                    continue
                
                # Find corresponding memory record
                if key not in memory_lookup:
                    continue
                
                record = memory_lookup[key]
                
                # Validate placeholder signature
                source_text = record["source"]
                source_sig = record.get("placeholder_signature", "")
                
                is_entry_valid, entry_error = validate_translation_entry(
                    source_text, source_sig, text, key
                )
                
                if not is_entry_valid:
                    stats["validation_errors"] += 1
                    if logger:
                        logger.log_failure(
                            batch_id,
                            "placeholder_mismatch",
                            entry_error,
                            {"key": key}
                        )
                    continue
                
                # Update memory record
                if "targets" not in record:
                    record["targets"] = {}
                if "status" not in record:
                    record["status"] = {}
                
                record["targets"][target_lang] = text
                record["status"][target_lang] = "ok"
                stats["items_translated"] += 1
                stats["updated_records"] += 1
            
            stats["batches_processed"] += 1
        
        except Exception as e:
            stats["items_failed"] += len(batch)
            if logger:
                logger.log_failure(batch_id, "translation_error", str(e))
    
    # Write updated memory.jsonl
    with open(memory_file, "w", encoding="utf-8") as f:
        for record in memory_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    return stats



