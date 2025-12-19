"""Per-run logging for translation operations."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class RunLogger:
    """Logger for translation runs."""
    
    def __init__(self, runs_dir: Path, run_id: Optional[str] = None):
        """
        Initialize run logger.
        
        Args:
            runs_dir: Base directory for run logs (e.g., work/runs)
            run_id: Optional run ID. If None, generates a new UUID.
        """
        self.runs_dir = runs_dir
        self.run_id = run_id or str(uuid.uuid4())
        self.run_dir = runs_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log files
        self.requests_file = self.run_dir / "requests.jsonl"
        self.responses_file = self.run_dir / "responses.jsonl"
        self.failures_file = self.run_dir / "failures.jsonl"
        self.summary_file = self.run_dir / "summary.json"
        
        # Initialize summary
        self.summary = {
            "run_id": self.run_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "target_language": None,
            "batches_processed": 0,
            "items_translated": 0,
            "items_failed": 0,
            "validation_errors": 0,
            "repair_attempts": 0,
        }
    
    def log_request(
        self,
        batch_id: int,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]]
    ) -> None:
        """
        Log a translation request.
        
        Args:
            batch_id: Batch identifier
            source_lang: Source language code
            target_lang: Target language code
            items: List of items in the batch
        """
        request_record = {
            "batch_id": batch_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "items": items,
            "item_count": len(items)
        }
        
        with open(self.requests_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(request_record, ensure_ascii=False) + "\n")
    
    def log_response(
        self,
        batch_id: int,
        response: Dict[str, Any],
        success: bool = True
    ) -> None:
        """
        Log a translation response.
        
        Args:
            batch_id: Batch identifier
            response: Response dictionary from provider
            success: Whether the response was successful
        """
        response_record = {
            "batch_id": batch_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "success": success,
            "response": response
        }
        
        with open(self.responses_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(response_record, ensure_ascii=False) + "\n")
    
    def log_failure(
        self,
        batch_id: int,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a translation failure.
        
        Args:
            batch_id: Batch identifier
            error_type: Type of error (e.g., "validation_error", "api_error")
            error_message: Error message
            context: Optional context dictionary
        """
        failure_record = {
            "batch_id": batch_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        
        with open(self.failures_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(failure_record, ensure_ascii=False) + "\n")
        
        self.summary["items_failed"] += 1
    
    def update_summary(
        self,
        target_language: Optional[str] = None,
        batches_processed: Optional[int] = None,
        items_translated: Optional[int] = None,
        validation_errors: Optional[int] = None,
        repair_attempts: Optional[int] = None
    ) -> None:
        """
        Update summary statistics.
        
        Args:
            target_language: Target language code
            batches_processed: Number of batches processed
            items_translated: Number of items translated
            validation_errors: Number of validation errors
            repair_attempts: Number of repair attempts
        """
        if target_language is not None:
            self.summary["target_language"] = target_language
        if batches_processed is not None:
            self.summary["batches_processed"] = batches_processed
        if items_translated is not None:
            self.summary["items_translated"] = items_translated
        if validation_errors is not None:
            self.summary["validation_errors"] = validation_errors
        if repair_attempts is not None:
            self.summary["repair_attempts"] = repair_attempts
    
    def finalize(self) -> None:
        """Finalize the run and write summary."""
        self.summary["completed_at"] = datetime.utcnow().isoformat() + "Z"
        
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current summary."""
        return self.summary.copy()

