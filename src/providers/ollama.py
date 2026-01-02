"""Ollama provider for local LLM translation."""

import json
import subprocess
from typing import List, Dict, Any, Optional

from src.providers.base import TranslationProvider
from src.providers.utils import extract_json_from_response, fix_json_escaping
from src.prompts.translate import build_translation_prompt
from src.prompts.repair import build_repair_prompt
from src.validate.schema import validate_llm_output, validate_translation_entry


class OllamaProvider(TranslationProvider):
    """Ollama provider for local LLM translation."""
    
    def __init__(self, model: str = "llama3.1:latest", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            model: Ollama model name (default: "llama3.1:latest")
            base_url: Ollama API base URL (default: "http://localhost:11434")
        """
        self.model = model
        self.base_url = base_url
    
    def _call_ollama(self, prompt: str, temperature: float = 0.1) -> str:
        """
        Call Ollama API with a prompt.
        
        Args:
            prompt: Prompt text
            temperature: Temperature for generation (default: 0.1 for deterministic)
        
        Returns:
            Response text from Ollama
        """
        # Use ollama command-line tool
        cmd = [
            "ollama",
            "run",
            self.model,
            prompt
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid characters instead of crashing
                timeout=300,  # 5 minute timeout
                check=True
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise Exception(f"Ollama request timed out after 300 seconds")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ollama request failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("Ollama not found. Please install Ollama and ensure it's in your PATH.")
    
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate a batch of items using Ollama.
        
        Includes repair flow for invalid JSON responses (max 2 attempts).
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            items: List of items to translate
        
        Returns:
            Validated translation response dictionary
        """
        if not items:
            return {
                "targetLanguage": target_lang,
                "translations": []
            }
        
        # Build initial prompt with context
        prompt = build_translation_prompt(
            source_lang, 
            target_lang, 
            items,
            global_context=global_context,
            per_key_context=per_key_context
        )
        
        # Try translation with repair flow (max 2 repair attempts)
        max_repairs = 2
        for attempt in range(max_repairs + 1):
            try:
                # Call Ollama
                response_text = self._call_ollama(prompt)
                
                # Extract JSON from response (might be wrapped in markdown or have commentary)
                response_text = extract_json_from_response(response_text)
                
                # Preprocess: Try to fix common JSON escaping issues with protected tokens
                # If response contains unescaped \1, \2, etc. in JSON strings, try to fix them
                response_text = fix_json_escaping(response_text)
                
                # Validate response
                is_valid, data, error_msg = validate_llm_output(response_text)
                
                if is_valid:
                    # Validate each translation entry
                    source_signatures = {
                        item["key"]: item.get("signature", "")
                        for item in items
                    }
                    
                    # Note: We'll need to pass signatures from memory records
                    # For now, we'll skip per-entry validation if signatures aren't provided
                    return data
                else:
                    # Invalid response - try repair
                    if attempt < max_repairs:
                        repair_prompt = build_repair_prompt(response_text, prompt, error_msg)
                        prompt = repair_prompt
                        continue
                    else:
                        raise Exception(f"Translation failed after {max_repairs} repair attempts: {error_msg}")
            
            except Exception as e:
                if attempt < max_repairs:
                    # Try repair on exception too
                    repair_prompt = build_repair_prompt("", prompt, str(e))
                    prompt = repair_prompt
                    continue
                else:
                    raise
        
        raise Exception("Translation failed: max repairs exceeded")

