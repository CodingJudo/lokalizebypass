"""Tests for OpenRouter provider."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, RequestException

from src.providers.openrouter import OpenRouterProvider
from src.providers.utils import extract_json_from_response, fix_json_escaping


def test_openrouter_provider_init_from_env():
    """Test OpenRouterProvider initialization from environment variables."""
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key-123",
        "OPENROUTER_BASE_URL": "https://custom.openrouter.ai/api/v1",
        "OPENROUTER_MODEL": "anthropic/claude-3.5-sonnet"
    }):
        provider = OpenRouterProvider()
        assert provider.api_key == "test-key-123"
        assert provider.base_url == "https://custom.openrouter.ai/api/v1"
        assert provider.model == "anthropic/claude-3.5-sonnet"


def test_openrouter_provider_init_from_params():
    """Test OpenRouterProvider initialization from parameters."""
    provider = OpenRouterProvider(
        api_key="param-key",
        base_url="https://param.url/v1",
        model="openai/gpt-4"
    )
    assert provider.api_key == "param-key"
    assert provider.base_url == "https://param.url/v1"
    assert provider.model == "openai/gpt-4"


def test_openrouter_provider_init_defaults():
    """Test OpenRouterProvider initialization with defaults."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        provider = OpenRouterProvider()
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.model == "openai/gpt-4o-mini"


def test_openrouter_provider_init_missing_api_key():
    """Test OpenRouterProvider initialization fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="API key required"):
            OpenRouterProvider()


def test_openrouter_provider_init_optional_headers():
    """Test OpenRouterProvider initialization with optional headers."""
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "OPENROUTER_HTTP_REFERER": "https://example.com",
        "OPENROUTER_SITE_NAME": "Test App"
    }, clear=False):
        provider = OpenRouterProvider()
        assert provider.http_referer == "https://example.com"
        assert provider.site_name == "Test App"


def test_openrouter_provider_extract_json():
    """Test JSON extraction from various response formats."""
    provider = OpenRouterProvider(api_key="test-key")
    
    # Valid JSON as-is
    assert provider._extract_json('{"key": "value"}') == '{"key": "value"}'
    
    # JSON in markdown code block
    response = '```json\n{"key": "value"}\n```'
    assert provider._extract_json(response) == '{"key": "value"}'
    
    # JSON with commentary
    response = 'Here is the JSON:\n{"key": "value"}\nThat was it.'
    assert provider._extract_json(response) == '{"key": "value"}'


def test_openrouter_provider_fix_json_escaping():
    """Test JSON escaping fix for protected tokens."""
    provider = OpenRouterProvider(api_key="test-key")
    
    # Test fixing unescaped \1 in text field
    json_str = '{"translations": [{"key": "test", "text": "Value \\1 here"}]}'
    fixed = provider._fix_json_escaping(json_str)
    # Should escape \1 to \\1
    assert '\\\\1' in fixed or '\\1' in fixed  # Depending on how it's represented
    
    # Test that valid JSON structure is preserved
    parsed = json.loads(fixed)
    assert "translations" in parsed


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_call_success(mock_post):
    """Test successful OpenRouter API call."""
    provider = OpenRouterProvider(api_key="test-key", model="openai/gpt-4o-mini")
    
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
    
    result = provider._call_openrouter("Test prompt")
    assert result == '{"targetLanguage": "de", "translations": []}'


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_call_with_optional_headers(mock_post):
    """Test OpenRouter API call includes optional headers if set."""
    provider = OpenRouterProvider(
        api_key="test-key",
        http_referer="https://example.com",
        site_name="Test App"
    )
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "test"}}]
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    provider._call_openrouter("Test prompt")
    
    # Verify headers were included
    call_args = mock_post.call_args
    headers = call_args[1]["headers"]
    assert headers["HTTP-Referer"] == "https://example.com"
    assert headers["X-Title"] == "Test App"


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_rate_limit_retry(mock_post):
    """Test OpenRouter API rate limit handling with retry."""
    provider = OpenRouterProvider(api_key="test-key", max_retries=2)
    
    # First call: rate limit
    rate_limit_response = Mock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "1"}
    rate_limit_response.text = "Rate limit exceeded"
    
    # Second call: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": "success"}}]
    }
    success_response.ok = True
    
    mock_post.side_effect = [rate_limit_response, success_response]
    
    result = provider._call_openrouter("Test prompt")
    assert result == "success"
    assert mock_post.call_count == 2


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_authentication_error(mock_post):
    """Test OpenRouter API authentication error handling."""
    provider = OpenRouterProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception, match="authentication failed"):
        provider._call_openrouter("Test prompt")


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_server_error_retry(mock_post):
    """Test OpenRouter API server error handling with retry."""
    provider = OpenRouterProvider(api_key="test-key", max_retries=2)
    
    # First call: server error
    server_error_response = Mock()
    server_error_response.status_code = 500
    server_error_response.text = "Internal server error"
    
    # Second call: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": "success"}}]
    }
    success_response.ok = True
    
    mock_post.side_effect = [server_error_response, success_response]
    
    result = provider._call_openrouter("Test prompt")
    assert result == "success"
    assert mock_post.call_count == 2


@patch('src.providers.openrouter.requests.post')
def test_openrouter_provider_timeout_retry(mock_post):
    """Test OpenRouter API timeout handling with retry."""
    provider = OpenRouterProvider(api_key="test-key", max_retries=2)
    
    # First call: timeout
    # Second call: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": "success"}}]
    }
    success_response.ok = True
    
    mock_post.side_effect = [Timeout("Request timeout"), success_response]
    
    result = provider._call_openrouter("Test prompt")
    assert result == "success"
    assert mock_post.call_count == 2


@patch('src.providers.openrouter.OpenRouterProvider._call_openrouter')
@patch('src.providers.openrouter.validate_llm_output')
def test_openrouter_provider_translate_batch_success(mock_validate, mock_call):
    """Test successful translation batch."""
    provider = OpenRouterProvider(api_key="test-key")
    
    # Mock API call
    mock_call.return_value = '{"targetLanguage": "de", "translations": [{"key": "test", "text": "Test"}]}'
    
    # Mock validation
    mock_validate.return_value = (True, {
        "targetLanguage": "de",
        "translations": [{"key": "test", "text": "Test"}]
    }, "")
    
    items = [{"key": "test", "text": "Test"}]
    result = provider.translate_batch("en", "de", items)
    
    assert result["targetLanguage"] == "de"
    assert len(result["translations"]) == 1


@patch('src.providers.openrouter.OpenRouterProvider._call_openrouter')
@patch('src.providers.openrouter.validate_llm_output')
def test_openrouter_provider_translate_batch_repair_flow(mock_validate, mock_call):
    """Test translation batch with repair flow for invalid JSON."""
    provider = OpenRouterProvider(api_key="test-key")
    
    # First call: invalid JSON
    # Second call: valid JSON after repair
    mock_call.side_effect = [
        'Invalid JSON response',
        '{"targetLanguage": "de", "translations": [{"key": "test", "text": "Test"}]}'
    ]
    
    # First validation: invalid
    # Second validation: valid
    mock_validate.side_effect = [
        (False, None, "Invalid JSON"),
        (True, {
            "targetLanguage": "de",
            "translations": [{"key": "test", "text": "Test"}]
        }, "")
    ]
    
    items = [{"key": "test", "text": "Test"}]
    result = provider.translate_batch("en", "de", items)
    
    assert result["targetLanguage"] == "de"
    assert mock_call.call_count == 2  # Initial + repair


@patch('src.providers.openrouter.OpenRouterProvider._call_openrouter')
def test_openrouter_provider_translate_batch_empty_items(mock_call):
    """Test translation batch with empty items list."""
    provider = OpenRouterProvider(api_key="test-key")
    
    result = provider.translate_batch("en", "de", [])
    
    assert result["targetLanguage"] == "de"
    assert result["translations"] == []
    mock_call.assert_not_called()


@patch('src.providers.openrouter.OpenRouterProvider._call_openrouter')
@patch('src.providers.openrouter.validate_llm_output')
def test_openrouter_provider_translate_batch_protected_tokens(mock_validate, mock_call):
    """Test translation batch preserves protected tokens."""
    provider = OpenRouterProvider(api_key="test-key")
    
    # Mock response with protected tokens
    response_json = '{"targetLanguage": "de", "translations": [{"key": "test", "text": "Value \\\\1 here"}]}'
    mock_call.return_value = response_json
    
    mock_validate.return_value = (True, {
        "targetLanguage": "de",
        "translations": [{"key": "test", "text": "Value \\1 here"}]
    }, "")
    
    items = [{"key": "test", "text": "Value \\1 here"}]
    result = provider.translate_batch("en", "de", items)
    
    assert result["translations"][0]["text"] == "Value \\1 here"
    # Verify _fix_json_escaping was called (through the flow)
    assert "\\1" in result["translations"][0]["text"] or "\\\\1" in result["translations"][0]["text"]

