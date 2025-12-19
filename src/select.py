"""Compute missing keys and batching strategy."""

from typing import List, Dict, Any
from collections import defaultdict


def get_missing_keys(
    memory_records: List[Dict[str, Any]],
    target_lang: str
) -> List[Dict[str, Any]]:
    """
    Get list of missing translation keys for a target language.
    
    Args:
        memory_records: List of memory records from memory.jsonl
        target_lang: Target language code
    
    Returns:
        List of records with missing translations, each including:
        - key: Translation key
        - text: Source text
        - signature: Placeholder signature
    """
    missing = []
    
    for record in memory_records:
        # Check if translation is missing for target language
        status = record.get("status", {})
        if status.get(target_lang) == "missing":
            missing.append({
                "key": record["key"],
                "text": record["source"],
                "signature": record.get("placeholder_signature", "")
            })
    
    return missing


def batch_by_namespace(
    items: List[Dict[str, Any]],
    batch_size: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Batch items by namespace with stable ordering.
    
    Groups items by namespace (extracted from key prefix before first dot),
    then batches within each namespace. Maintains stable ordering.
    
    Args:
        items: List of items to batch, each with "key" field
        batch_size: Maximum items per batch (default: 10)
    
    Returns:
        List of batches, each batch is a list of items
    """
    # Group by namespace
    by_namespace = defaultdict(list)
    
    for item in items:
        key = item["key"]
        if "." in key:
            namespace = key.split(".", 1)[0]
        else:
            namespace = "default"
        
        by_namespace[namespace].append(item)
    
    # Create batches within each namespace
    batches = []
    
    # Sort namespaces for deterministic ordering
    for namespace in sorted(by_namespace.keys()):
        namespace_items = by_namespace[namespace]
        
        # Sort items by key for stable ordering
        namespace_items.sort(key=lambda x: x["key"])
        
        # Batch items
        for i in range(0, len(namespace_items), batch_size):
            batch = namespace_items[i:i + batch_size]
            batches.append(batch)
    
    return batches


def batch_by_prefix(
    items: List[Dict[str, Any]],
    prefix_length: int = 2,
    batch_size: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Batch items by key prefix with stable ordering.
    
    Groups items by the first N characters of the key,
    then batches within each prefix group.
    
    Args:
        items: List of items to batch, each with "key" field
        prefix_length: Length of prefix to group by (default: 2)
        batch_size: Maximum items per batch (default: 10)
    
    Returns:
        List of batches, each batch is a list of items
    """
    # Group by prefix
    by_prefix = defaultdict(list)
    
    for item in items:
        key = item["key"]
        prefix = key[:prefix_length] if len(key) >= prefix_length else key
        by_prefix[prefix].append(item)
    
    # Create batches within each prefix
    batches = []
    
    # Sort prefixes for deterministic ordering
    for prefix in sorted(by_prefix.keys()):
        prefix_items = by_prefix[prefix]
        
        # Sort items by key for stable ordering
        prefix_items.sort(key=lambda x: x["key"])
        
        # Batch items
        for i in range(0, len(prefix_items), batch_size):
            batch = prefix_items[i:i + batch_size]
            batches.append(batch)
    
    return batches

