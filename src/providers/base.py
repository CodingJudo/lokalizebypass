"""Base provider interface for translation."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class TranslationProvider(ABC):
    """Base class for translation providers."""
    
    @abstractmethod
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate a batch of items from source language to target language.
        
        Args:
            source_lang: Source language code (e.g., "sv")
            target_lang: Target language code (e.g., "de")
            items: List of items to translate, each with "key" and "text"
                Example: [{"key": "booking.confirm", "text": "Bekräfta bokning"}]
            global_context: Optional global context string for all translations
            per_key_context: Optional dict mapping keys to context dicts
                Example: {"booking.confirm": {"description": "CTA button", "tone": "friendly"}}
        
        Returns:
            Dictionary with LLM response format:
            {
                "targetLanguage": "de",
                "translations": [
                    {"key": "booking.confirm", "text": "Buchung bestätigen"}
                ]
            }
        
        Raises:
            Exception: If translation fails
        """
        pass

