"""OpenAI provider for LLM translation."""

import json
import os
import time
from typing import List, Dict, Any, Optional
import requests

from src.providers.base import TranslationProvider
from src.prompts.translate import build_translation_prompt
from src.prompts.repair import build_repair_prompt
from src.validate.schema import validate_llm_output


class OpenAIProvider(TranslationProvider):
    """OpenAI provider for LLM translation using Chat Completions API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (default: from OPENAI_API_KEY env var)
            base_url: API base URL (default: from OPENAI_BASE_URL env var or https://api.openai.com/v1)
            model: Model name (default: from OPENAI_MODEL env var or gpt-4o-mini)
            max_retries: Maximum number of retries on failure (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 60.0)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or 
                        "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks and commentary.
        
        Args:
            text: Raw response text from LLM
        
        Returns:
            Extracted JSON string
        """
        import re
        
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
    
    def _call_openai(
        self,
        prompt: str,
        temperature: float = 0.1
    ) -> str:
        """
        Call OpenAI Chat Completions API with a prompt.
        
        Args:
            prompt: Prompt text
            temperature: Temperature for generation (default: 0.1 for deterministic)
            logger: Optional RunLogger instance for logging
        
        Returns:
            Response text from OpenAI
        
        Raises:
            Exception: If API call fails after retries
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert prompt to chat messages format
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}  # JSON mode if supported
        }
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Handle rate limits (429) with exponential backoff
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        wait_time = self.retry_delay * (2 ** attempt)
                    
                    if attempt < self.max_retries:
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"OpenAI API rate limit exceeded after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                # Handle authentication errors (401)
                if response.status_code == 401:
                    raise Exception(
                        "OpenAI API authentication failed. Check your API key. "
                        f"Response: {response.text}"
                    )
                
                # Handle permission errors (403)
                if response.status_code == 403:
                    raise Exception(
                        "OpenAI API permission denied. Check your API key permissions. "
                        f"Response: {response.text}"
                    )
                
                # Handle server errors (500, 502, 503) with retry
                if response.status_code in [500, 502, 503]:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"OpenAI API server error ({response.status_code}) after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                # Handle other HTTP errors
                if not response.ok:
                    raise Exception(
                        f"OpenAI API error ({response.status_code}): {response.text}"
                    )
                
                # Parse response
                response_data = response.json()
                
                # Extract content from response
                if "choices" not in response_data or len(response_data["choices"]) == 0:
                    raise Exception("OpenAI API response missing choices")
                
                content = response_data["choices"][0]["message"]["content"]
                return content.strip()
            
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"OpenAI API request timed out after {self.max_retries} retries: {e}")
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"OpenAI API request failed after {self.max_retries} retries: {e}")
        
        # Should not reach here, but just in case
        raise Exception(f"OpenAI API request failed: {last_exception}")
    
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate a batch of items using OpenAI.
        
        Includes repair flow for invalid JSON responses (max 2 attempts).
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            items: List of items to translate
            global_context: Optional global context string
            per_key_context: Optional per-key context dict
        
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
                # Call OpenAI
                response_text = self._call_openai(prompt)
                
                # Extract JSON from response (might be wrapped in markdown or have commentary)
                response_text = self._extract_json(response_text)
                
                # Preprocess: Try to fix common JSON escaping issues with protected tokens
                # If response contains unescaped \1, \2, etc. in JSON strings, try to fix them
                response_text = self._fix_json_escaping(response_text)
                
                # Validate response
                is_valid, data, error_msg = validate_llm_output(response_text)
                
                if is_valid:
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

