"""Claude (Anthropic) provider for LLM translation."""

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


class ClaudeProvider(TranslationProvider):
    """Claude (Anthropic) provider for LLM translation using Messages API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
        use_batch_api: bool = False,
        batch_threshold: int = 100
    ):
        """
        Initialize Claude provider.
        
        Args:
            api_key: Anthropic API key (default: from ANTHROPIC_API_KEY env var)
            base_url: API base URL (default: from ANTHROPIC_BASE_URL env var or https://api.anthropic.com/v1)
            model: Model name (default: from ANTHROPIC_MODEL env var or claude-3-5-sonnet-20241022)
            max_retries: Maximum number of retries on failure (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 60.0)
            use_batch_api: If True, use asynchronous batch API (default: False)
            batch_threshold: Auto-use batch API if items > threshold (default: 100)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.base_url = (base_url or os.getenv("ANTHROPIC_BASE_URL") or 
                        "https://api.anthropic.com/v1")
        self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.use_batch_api = use_batch_api
        self.batch_threshold = batch_threshold
    
    def _call_claude_messages(
        self,
        prompt: str,
        temperature: float = 0.1
    ) -> str:
        """
        Call Anthropic Messages API with a prompt.
        
        Args:
            prompt: Prompt text
            temperature: Temperature for generation (default: 0.1)
        
        Returns:
            Response text from Claude
        
        Raises:
            Exception: If API call fails after retries
        """
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
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
                            f"Anthropic API rate limit exceeded after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                if response.status_code == 401:
                    raise Exception(
                        "Anthropic API authentication failed. Check your API key. "
                        f"Response: {response.text}"
                    )
                
                if response.status_code == 403:
                    raise Exception(
                        "Anthropic API permission denied. Check your API key permissions. "
                        f"Response: {response.text}"
                    )
                
                if response.status_code in [500, 502, 503]:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"Anthropic API server error ({response.status_code}) after {self.max_retries} retries. "
                            f"Response: {response.text}"
                        )
                
                if not response.ok:
                    raise Exception(
                        f"Anthropic API error ({response.status_code}): {response.text}"
                    )
                
                response_data = response.json()
                
                # Extract content from Anthropic response format
                if "content" not in response_data or len(response_data["content"]) == 0:
                    raise Exception("Anthropic API response missing content")
                
                # Anthropic returns content as array of content blocks
                # Extract text from first content block
                content_block = response_data["content"][0]
                if content_block.get("type") != "text":
                    raise Exception(f"Anthropic API returned non-text content: {content_block.get('type')}")
                
                return content_block.get("text", "").strip()
            
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Anthropic API request timed out after {self.max_retries} retries: {e}")
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Anthropic API request failed after {self.max_retries} retries: {e}")
        
        raise Exception(f"Anthropic API request failed: {last_exception}")
    
    def _create_batch(
        self,
        requests_list: List[Dict[str, Any]]
    ) -> str:
        """
        Create a batch of requests for asynchronous processing.
        
        Args:
            requests_list: List of request dicts with custom_id and params
        
        Returns:
            Batch ID
        
        Raises:
            Exception: If batch creation fails
        """
        url = f"{self.base_url}/messages/batches"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "requests": requests_list
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        
        if not response.ok:
            raise Exception(
                f"Failed to create batch: {response.status_code} - {response.text}"
            )
        
        batch_data = response.json()
        return batch_data["id"]
    
    def _get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get batch processing status.
        
        Args:
            batch_id: Batch ID
        
        Returns:
            Batch status dictionary
        """
        url = f"{self.base_url}/messages/batches/{batch_id}"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        response = requests.get(url, headers=headers, timeout=self.timeout)
        
        if not response.ok:
            raise Exception(
                f"Failed to get batch status: {response.status_code} - {response.text}"
            )
        
        return response.json()
    
    def _poll_batch_status(self, batch_id: str, max_wait_hours: float = 24.0) -> Dict[str, Any]:
        """
        Poll batch status until processing is complete.
        
        Args:
            batch_id: Batch ID
            max_wait_hours: Maximum wait time in hours (default: 24)
        
        Returns:
            Final batch status dictionary
        
        Raises:
            Exception: If batch fails or exceeds max wait time
        """
        max_wait_seconds = max_wait_hours * 3600
        poll_interval = 60  # Poll every 60 seconds
        start_time = time.time()
        
        while True:
            status_data = self._get_batch_status(batch_id)
            processing_status = status_data.get("processing_status")
            
            if processing_status == "ended":
                return status_data
            elif processing_status in ["expired", "cancelled"]:
                raise Exception(f"Batch {batch_id} {processing_status}")
            elif time.time() - start_time > max_wait_seconds:
                raise Exception(f"Batch {batch_id} exceeded max wait time ({max_wait_hours} hours)")
            
            # Still processing - wait and poll again
            time.sleep(poll_interval)
    
    def _get_batch_results(self, results_url: str) -> List[Dict[str, Any]]:
        """
        Retrieve batch results from results URL.
        
        Args:
            results_url: URL to retrieve results from
        
        Returns:
            List of result dictionaries (JSONL format)
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        response = requests.get(results_url, headers=headers, timeout=self.timeout)
        
        if not response.ok:
            raise Exception(
                f"Failed to retrieve batch results: {response.status_code} - {response.text}"
            )
        
        # Results are in JSONL format (one JSON object per line)
        results = []
        for line in response.text.strip().split('\n'):
            if line.strip():
                results.append(json.loads(line))
        
        return results
    
    def _translate_batch_sync(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate batch using synchronous Messages API.
        
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
        
        prompt = build_translation_prompt(
            source_lang,
            target_lang,
            items,
            global_context=global_context,
            per_key_context=per_key_context
        )
        
        max_repairs = 2
        for attempt in range(max_repairs + 1):
            try:
                response_text = self._call_claude_messages(prompt)
                response_text = extract_json_from_response(response_text)
                response_text = fix_json_escaping(response_text)
                
                is_valid, data, error_msg = validate_llm_output(response_text)
                
                if is_valid:
                    return data
                else:
                    if attempt < max_repairs:
                        repair_prompt = build_repair_prompt(response_text, prompt, error_msg)
                        prompt = repair_prompt
                        continue
                    else:
                        raise Exception(f"Translation failed after {max_repairs} repair attempts: {error_msg}")
            
            except Exception as e:
                if attempt < max_repairs:
                    repair_prompt = build_repair_prompt("", prompt, str(e))
                    prompt = repair_prompt
                    continue
                else:
                    raise
        
        raise Exception("Translation failed: max repairs exceeded")
    
    def _translate_batch_async(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate batch using asynchronous Batch API.
        
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
        
        # Build prompts for each item
        # For batch API, we create one request per item (or group items)
        # For simplicity, create one request per item
        requests_list = []
        
        for idx, item in enumerate(items):
            # Build prompt for single item
            single_item_prompt = build_translation_prompt(
                source_lang,
                target_lang,
                [item],
                global_context=global_context,
                per_key_context={item["key"]: per_key_context[item["key"]]} if per_key_context and item["key"] in per_key_context else None
            )
            
            requests_list.append({
                "custom_id": f"item-{idx}-{item['key']}",
                "params": {
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "user", "content": single_item_prompt}
                    ],
                    "temperature": 0.1
                }
            })
        
        # Create batch
        batch_id = self._create_batch(requests_list)
        
        # Poll for completion
        status_data = self._poll_batch_status(batch_id)
        
        # Retrieve results
        results_url = status_data.get("results_url")
        if not results_url:
            raise Exception(f"Batch {batch_id} completed but no results_url provided")
        
        results = self._get_batch_results(results_url)
        
        # Process results and combine into single response
        all_translations = []
        for result in results:
            custom_id = result.get("custom_id", "")
            output = result.get("output", {})
            
            if "error" in result:
                # Skip failed items
                continue
            
            # Extract content from output
            content = output.get("content", [])
            if not content or content[0].get("type") != "text":
                continue
            
            response_text = content[0].get("text", "")
            response_text = extract_json_from_response(response_text)
            response_text = fix_json_escaping(response_text)
            
            # Validate and extract translations
            is_valid, data, _ = validate_llm_output(response_text)
            if is_valid and "translations" in data:
                all_translations.extend(data["translations"])
        
        return {
            "targetLanguage": target_lang,
            "translations": all_translations
        }
    
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        global_context: Optional[str] = None,
        per_key_context: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Translate a batch of items using Claude.
        
        Automatically chooses between synchronous and asynchronous batch API
        based on use_batch_api flag and item count.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            items: List of items to translate
            global_context: Optional global context string
            per_key_context: Optional per-key context dict
        
        Returns:
            Validated translation response dictionary
        """
        # Auto-detect: use batch API if explicitly requested or items > threshold
        should_use_batch = self.use_batch_api or len(items) > self.batch_threshold
        
        if should_use_batch:
            return self._translate_batch_async(
                source_lang, target_lang, items, global_context, per_key_context
            )
        else:
            return self._translate_batch_sync(
                source_lang, target_lang, items, global_context, per_key_context
            )

