"""Ollama provider for local LLM translation."""

import json
import subprocess
from typing import List, Dict, Any, Optional

from src.providers.base import TranslationProvider
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
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks and commentary.
        
        Args:
            text: Raw response text from LLM
        
        Returns:
            Extracted JSON string
        """
        import re
        import json
        
        # Try to parse as-is first
        try:
            json.loads(text.strip())
            return text.strip()
        except:
            pass
        
        # Try to extract JSON from markdown code blocks
        # Pattern: ```json ... ``` or ``` ... ```
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except:
                pass
        
        # Try to find JSON object in the text
        # Look for { ... } that might be valid JSON
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except:
                pass
        
        # If nothing found, return original (will fail validation)
        return text.strip()
    
    def _fix_json_escaping(self, text: str) -> str:
        """
        Fix common JSON escaping issues with protected tokens.
        
        Attempts to fix cases where backslash-number tokens (\1, \2, etc.)
        are not properly escaped in JSON strings. In JSON, backslashes must be
        escaped, so \1 should be written as \\1.
        
        Also handles control characters (like \x01) that result from unescaped \1.
        Excludes common escape sequences like \n, \t, etc.
        
        Args:
            text: Raw response text from LLM
        
        Returns:
            Potentially fixed text
        """
        import re
        
        # Only fix backslash-number tokens in "text" field values
        # Don't touch the JSON structure itself (newlines, etc.)
        def fix_text_field(match):
            field_start = match.group(1)  # "text": "
            string_content = match.group(2)  # content between quotes
            field_end = match.group(3)  # closing quote
            
            # Fix unescaped backslash-number patterns (\1, \2, etc.)
            # Replace \1, \2, etc. with \\1, \\2, etc.
            # But avoid double-escaping (don't replace \\1)
            # Also avoid common escape sequences like \n, \t, \r
            fixed_content = re.sub(r'(?<!\\)\\([0-9]+)', r'\\\\\1', string_content)
            
            # Also fix control characters that might result from unescaped \1, \2, etc.
            # But exclude common ones: \n (10), \t (9), \r (13)
            def fix_control_char(match_char):
                char_code = ord(match_char.group(0))
                # Only fix control chars that are likely from \1, \2, etc. (1-8, 11-12, 14-31)
                # Exclude: \t (9), \n (10), \r (13)
                if (1 <= char_code <= 8) or (11 <= char_code <= 12) or (14 <= char_code <= 31):
                    return f'\\\\{char_code}'
                return match_char.group(0)
            
            # Fix control characters in the string content
            fixed_content = re.sub(r'[\x01-\x08\x0B-\x0C\x0E-\x1F]', fix_control_char, fixed_content)
            
            return f'{field_start}{fixed_content}{field_end}'
        
        # Pattern to match "text": "..." fields
        pattern = r'("text"\s*:\s*")(.*?)(")'
        fixed = re.sub(pattern, fix_text_field, text, flags=re.DOTALL)
        
        return fixed
    
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
                response_text = self._extract_json(response_text)
                
                # Preprocess: Try to fix common JSON escaping issues with protected tokens
                # If response contains unescaped \1, \2, etc. in JSON strings, try to fix them
                response_text = self._fix_json_escaping(response_text)
                
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

