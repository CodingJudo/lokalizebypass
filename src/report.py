"""Generate summary reports for translation runs."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

from src.memory import is_missing


def generate_summary_report(
    memory_file: Path,
    target_lang: str,
    run_stats: Dict[str, Any],
    before_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a summary report for a translation run.
    
    Args:
        memory_file: Path to memory.jsonl file
        target_lang: Target language code
        run_stats: Statistics from translate_missing
        before_stats: Optional statistics before translation (for comparison)
    
    Returns:
        Dictionary with report data:
        {
            "target_language": str,
            "missing_before": int,
            "missing_after": int,
            "translated": int,
            "failed": int,
            "invalid": int,
            "needs_review": int,
            "batches_processed": int,
            "repair_attempts": int
        }
    """
    # Read memory records
    records = []
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    
    # Count statuses
    missing_after = 0
    ok_count = 0
    invalid_count = 0
    needs_review_count = 0
    
    for record in records:
        status = record.get("status", {}).get(target_lang, "missing")
        
        if status == "missing":
            missing_after += 1
        elif status == "ok":
            ok_count += 1
        elif status == "invalid":
            invalid_count += 1
        elif status == "needs_review":
            needs_review_count += 1
    
    # Calculate missing before
    missing_before = missing_after + run_stats.get("items_translated", 0)
    
    report = {
        "target_language": target_lang,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "translated": run_stats.get("items_translated", 0),
        "failed": run_stats.get("items_failed", 0),
        "invalid": run_stats.get("validation_errors", 0) + invalid_count,
        "needs_review": needs_review_count,
        "batches_processed": run_stats.get("batches_processed", 0),
        "repair_attempts": run_stats.get("repair_attempts", 0),
    }
    
    return report


def print_summary_report(report: Dict[str, Any]) -> None:
    """
    Print a formatted summary report.
    
    Args:
        report: Report dictionary from generate_summary_report
    """
    print("\n" + "=" * 60)
    print(f"Translation Summary: {report['target_language']}")
    print("=" * 60)
    print(f"Missing before:  {report['missing_before']}")
    print(f"Missing after:   {report['missing_after']}")
    print(f"Translated:      {report['translated']}")
    print(f"Failed:          {report['failed']}")
    print(f"Invalid:         {report['invalid']}")
    print(f"Needs review:    {report['needs_review']}")
    print(f"Batches:         {report['batches_processed']}")
    print(f"Repair attempts: {report['repair_attempts']}")
    print("=" * 60 + "\n")

