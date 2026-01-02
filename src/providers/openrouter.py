"""OpenRouter provider for LLM translation."""

import json
import os
import time
from typing import List, Dict, Any, Optional
import requests

from src.providers.base import TranslationProvider
from src.providers.utils import extract_json_from_response, fix_json_escaping
from src.prompts.translate import build_translation_prompt
from src.prompts.repair import build_repair_prompt
from src.validate.schema import validate_llm_output


class OpenRouterProvider(TranslationProvider):
    """OpenRouter provider for LLM translation using OpenAI-compatible Chat Completions API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
        http_referer: Optional[str] = None,
        site_name: Optional[str] = None
    ):
        """
        Initialize OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key (default: from OPENROUTER_API_KEY env var)
            base_url: API base URL (default: from OPENROUTER_BASE_URL env var or https://openrouter.ai/api/v1)
            model: Model name (default: from OPENROUTER_MODEL env var or openai/gpt-4o-mini)
            max_retries: Maximum number of retries on failure (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 60.0)
            http_referer: Optional HTTP-Referer header (default: from OPENROUTER_HTTP_REFERER env var)
            site_name: Optional X-Title header (default: from OPENROUTER_SITE_NAME env var)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL") or 
                        "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o-mini"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.http_referer = http_referer or os.getenv("OPENROUTER_HTTP_REFERER")
        self.site_name = site_name or os.getenv("OPENROUTER_SITE_NAME")
    
    def _call_openrouter(
        self,
        prompt: str,
        temperature: float = 0.1
    ) -> str:
        """
        Call OpenRouter Chat Completions API with a prompt.
        
        Args:
            prompt: Prompt text
            temperature: Temperature for generation (default: 0.1 for deterministic)
        
        Returns:
            Response text from OpenRouter
        
        Raises:
            Exception: If API call fails after retries
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Add optional headers if provided
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.site_name:
            headers["X-Title"] = self.site_name
        
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
                            f"OpenRouter API rate limit exceeded after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                # Handle authentication errors (401)
                if response.status_code == 401:
                    raise Exception(
                        "OpenRouter API authentication failed. Check your API key. "
                        f"Response: {response.text}"
                    )
                
                # Handle permission errors (403)
                if response.status_code == 403:
                    raise Exception(
                        "OpenRouter API permission denied. Check your API key permissions. "
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
                            f"OpenRouter API server error ({response.status_code}) after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                # Handle other HTTP errors
                if not response.ok:
                    raise Exception(
                        f"OpenRouter API error ({response.status_code}): {response.text}"
                    )
                
                # Parse response
                response_data = response.json()
                
                # Extract content from response
                if "choices" not in response_data or len(response_data["choices"]) == 0:
                    raise Exception("OpenRouter API response missing choices")
                
                content = response_data["choices"][0]["message"]["content"]
                return content.strip()
            
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"OpenRouter API request timed out after {self.max_retries} retries: {e}")
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"OpenRouter API request failed after {self.max_retries} retries: {e}")
        
        # Should not reach here, but just in case
        raise Exception(f"OpenRouter API request failed: {last_exception}")
    
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate a batch of items using OpenRouter.
        
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
                # Call OpenRouter
                response_text = self._call_openrouter(prompt)
                
                # Extract JSON from response (might be wrapped in markdown or have commentary)
                response_text = extract_json_from_response(response_text)
                
                # Preprocess: Try to fix common JSON escaping issues with protected tokens
                # If response contains unescaped \1, \2, etc. in JSON strings, try to fix them
                response_text = fix_json_escaping(response_text)
                
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

