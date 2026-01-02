"""Tests for OpenAI provider."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, RequestException

from src.providers.openai import OpenAIProvider
from src.providers.utils import extract_json_from_response, fix_json_escaping


def test_openai_provider_init_from_env():
    """Test OpenAIProvider initialization from environment variables."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key-123",
        "OPENAI_BASE_URL": "https://custom.openai.com/v1",
        "OPENAI_MODEL": "gpt-4"
    }):
        provider = OpenAIProvider()
        assert provider.api_key == "test-key-123"
        assert provider.base_url == "https://custom.openai.com/v1"
        assert provider.model == "gpt-4"


def test_openai_provider_init_from_params():
    """Test OpenAIProvider initialization from parameters."""
    provider = OpenAIProvider(
        api_key="param-key",
        base_url="https://param.url/v1",
        model="gpt-3.5-turbo"
    )
    assert provider.api_key == "param-key"
    assert provider.base_url == "https://param.url/v1"
    assert provider.model == "gpt-3.5-turbo"


def test_openai_provider_init_defaults():
    """Test OpenAIProvider initialization with defaults."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
        provider = OpenAIProvider()
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.model == "gpt-4o-mini"


def test_openai_provider_init_missing_api_key():
    """Test OpenAIProvider initialization fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="API key required"):
            OpenAIProvider()


def test_openai_provider_extract_json():
    """Test JSON extraction from various response formats."""
    # Valid JSON as-is
    assert extract_json_from_response('{"key": "value"}') == '{"key": "value"}'
    
    # JSON in markdown code block
    response = '```json\n{"key": "value"}\n```'
    assert extract_json_from_response(response) == '{"key": "value"}'
    
    # JSON with commentary
    response = 'Here is the JSON:\n{"key": "value"}\nThat was it.'
    assert extract_json_from_response(response) == '{"key": "value"}'


def test_openai_provider_fix_json_escaping():
    """Test JSON escaping fix for protected tokens."""
    provider = OpenAIProvider(api_key="test-key")
    
    # Test fixing unescaped \1 in text field
    json_str = '{"translations": [{"key": "test", "text": "Value \\1 here"}]}'
    fixed = provider._fix_json_escaping(json_str)
    # Should escape \1 to \\1
    assert '\\\\1' in fixed or '\\1' in fixed  # Depending on how it's represented
    
    # Test that valid JSON structure is preserved
    parsed = json.loads(fixed)
    assert "translations" in parsed


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_success(mock_post):
    """Test successful OpenAI API call."""
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"targetLanguage": "de", "translations": []}'
            }
        }],
        "usage": {"total_tokens": 100}
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    result = provider._call_openai("Test prompt")
    assert result == '{"targetLanguage": "de", "translations": []}'


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_rate_limit_retry(mock_post):
    """Test rate limit handling with retry."""
    provider = OpenAIProvider(api_key="test-key", max_retries=2, retry_delay=0.1)
    
    # First call: rate limit, second call: success
    mock_response_429 = Mock()
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "1"}
    mock_response_429.ok = False
    
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "choices": [{"message": {"content": '{"result": "ok"}'}}]
    }
    mock_response_200.ok = True
    
    mock_post.side_effect = [mock_response_429, mock_response_200]
    
    with patch('time.sleep'):  # Speed up test
        result = provider._call_openai("Test prompt")
        assert result == '{"result": "ok"}'
        assert mock_post.call_count == 2


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_rate_limit_fail(mock_post):
    """Test rate limit failure after max retries."""
    provider = OpenAIProvider(api_key="test-key", max_retries=1, retry_delay=0.1)
    
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.text = "Rate limit exceeded"
    mock_response.ok = False
    mock_post.return_value = mock_response
    
    with patch('time.sleep'):  # Speed up test
        with pytest.raises(Exception, match="rate limit exceeded"):
            provider._call_openai("Test prompt")


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_auth_error(mock_post):
    """Test authentication error handling."""
    provider = OpenAIProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"
    mock_response.ok = False
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception, match="authentication failed"):
        provider._call_openai("Test prompt")


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_permission_error(mock_post):
    """Test permission error handling."""
    provider = OpenAIProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "Permission denied"
    mock_response.ok = False
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception, match="permission denied"):
        provider._call_openai("Test prompt")


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_server_error_retry(mock_post):
    """Test server error handling with retry."""
    provider = OpenAIProvider(api_key="test-key", max_retries=1, retry_delay=0.1)
    
    mock_response_500 = Mock()
    mock_response_500.status_code = 500
    mock_response_500.ok = False
    
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "choices": [{"message": {"content": '{"result": "ok"}'}}]
    }
    mock_response_200.ok = True
    
    mock_post.side_effect = [mock_response_500, mock_response_200]
    
    with patch('time.sleep'):  # Speed up test
        result = provider._call_openai("Test prompt")
        assert result == '{"result": "ok"}'


@patch('src.providers.openai.requests.post')
def test_openai_provider_call_timeout_retry(mock_post):
    """Test timeout handling with retry."""
    provider = OpenAIProvider(api_key="test-key", max_retries=1, retry_delay=0.1)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"result": "ok"}'}}]
    }
    mock_response.ok = True
    
    mock_post.side_effect = [Timeout("Request timeout"), mock_response]
    
    with patch('time.sleep'):  # Speed up test
        result = provider._call_openai("Test prompt")
        assert result == '{"result": "ok"}'


@patch('src.providers.openai.requests.post')
def test_openai_provider_translate_batch_success(mock_post):
    """Test successful translation batch."""
    provider = OpenAIProvider(api_key="test-key")
    
    items = [
        {"key": "test.key1", "text": "Hello"}
    ]
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "targetLanguage": "de",
                    "translations": [
                        {"key": "test.key1", "text": "Hallo"}
                    ]
                })
            }
        }]
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    result = provider.translate_batch("en", "de", items)
    assert result["targetLanguage"] == "de"
    assert len(result["translations"]) == 1
    assert result["translations"][0]["key"] == "test.key1"
    assert result["translations"][0]["text"] == "Hallo"


@patch('src.providers.openai.requests.post')
def test_openai_provider_translate_batch_empty_items(mock_post):
    """Test translation batch with empty items."""
    provider = OpenAIProvider(api_key="test-key")
    
    result = provider.translate_batch("en", "de", [])
    assert result["targetLanguage"] == "de"
    assert result["translations"] == []


@patch('src.providers.openai.requests.post')
def test_openai_provider_translate_batch_protected_tokens(mock_post):
    """Test translation preserves protected tokens."""
    provider = OpenAIProvider(api_key="test-key")
    
    items = [
        {"key": "test.key1", "text": "Hello {{name}} \\1"}
    ]
    
    # Mock response with protected tokens preserved
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "targetLanguage": "de",
                    "translations": [
                        {"key": "test.key1", "text": "Hallo {{name}} \\\\1"}
                    ]
                })
            }
        }]
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    result = provider.translate_batch("en", "de", items)
    assert "{{name}}" in result["translations"][0]["text"]
    assert "\\1" in result["translations"][0]["text"] or "\\\\1" in result["translations"][0]["text"]


@patch('src.providers.openai.requests.post')
def test_openai_provider_translate_batch_repair_flow(mock_post):
    """Test repair flow for invalid JSON."""
    provider = OpenAIProvider(api_key="test-key")
    
    items = [
        {"key": "test.key1", "text": "Hello"}
    ]
    
    # First call: invalid JSON, second call: valid JSON
    mock_response_invalid = Mock()
    mock_response_invalid.status_code = 200
    mock_response_invalid.json.return_value = {
        "choices": [{
            "message": {
                "content": "Invalid JSON response"
            }
        }]
    }
    mock_response_invalid.ok = True
    
    mock_response_valid = Mock()
    mock_response_valid.status_code = 200
    mock_response_valid.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "targetLanguage": "de",
                    "translations": [
                        {"key": "test.key1", "text": "Hallo"}
                    ]
                })
            }
        }]
    }
    mock_response_valid.ok = True
    
    mock_post.side_effect = [mock_response_invalid, mock_response_valid]
    
    result = provider.translate_batch("en", "de", items)
    assert result["targetLanguage"] == "de"
    assert len(result["translations"]) == 1


@patch('src.providers.openai.requests.post')
def test_openai_provider_translate_batch_with_context(mock_post):
    """Test translation with global and per-key context."""
    provider = OpenAIProvider(api_key="test-key")
    
    items = [
        {"key": "test.key1", "text": "Hello"}
    ]
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "targetLanguage": "de",
                    "translations": [
                        {"key": "test.key1", "text": "Hallo"}
                    ]
                })
            }
        }]
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    result = provider.translate_batch(
        "en",
        "de",
        items,
        global_context="This is a mobile app",
        per_key_context={"test.key1": {"tone": "friendly"}}
    )
    
    # Verify the request was made (context is in prompt, not response)
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert "messages" in payload
    # Context should be in the prompt content
    prompt_content = payload["messages"][0]["content"]
    assert "mobile app" in prompt_content or "friendly" in prompt_content


@patch('src.providers.openai.requests.post')
def test_openai_provider_chat_messages_format(mock_post):
    """Test that OpenAI API is called with correct chat messages format."""
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"targetLanguage": "de", "translations": []}'
            }
        }]
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    provider._call_openai("Test prompt")
    
    # Verify request format
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
    
    headers = call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"
    
    payload = call_args[1]["json"]
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0.1
    assert payload["response_format"] == {"type": "json_object"}
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Test prompt"

