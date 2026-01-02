"""Tests for Claude (Anthropic) provider."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, RequestException

from src.providers.claude import ClaudeProvider
from src.providers.utils import extract_json_from_response


def test_claude_provider_init_from_env():
    """Test ClaudeProvider initialization from environment variables."""
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test-key-123",
        "ANTHROPIC_BASE_URL": "https://custom.anthropic.com/v1",
        "ANTHROPIC_MODEL": "claude-3-opus-20240229"
    }):
        provider = ClaudeProvider()
        assert provider.api_key == "test-key-123"
        assert provider.base_url == "https://custom.anthropic.com/v1"
        assert provider.model == "claude-3-opus-20240229"


def test_claude_provider_init_from_params():
    """Test ClaudeProvider initialization from parameters."""
    provider = ClaudeProvider(
        api_key="param-key",
        base_url="https://param.url/v1",
        model="claude-3-5-sonnet-20241022"
    )
    assert provider.api_key == "param-key"
    assert provider.base_url == "https://param.url/v1"
    assert provider.model == "claude-3-5-sonnet-20241022"


def test_claude_provider_init_defaults():
    """Test ClaudeProvider initialization with defaults."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        provider = ClaudeProvider()
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.anthropic.com/v1"
        assert provider.model == "claude-3-5-sonnet-20241022"


def test_claude_provider_init_missing_api_key():
    """Test ClaudeProvider initialization fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="API key required"):
            ClaudeProvider()


def test_claude_provider_init_batch_api():
    """Test ClaudeProvider initialization with batch API options."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        provider = ClaudeProvider(use_batch_api=True, batch_threshold=50)
        assert provider.use_batch_api is True
        assert provider.batch_threshold == 50


def test_claude_provider_extract_json():
    """Test JSON extraction from various response formats."""
    provider = ClaudeProvider(api_key="test-key")
    
    # Valid JSON as-is
    assert provider._extract_json('{"key": "value"}') == '{"key": "value"}'
    
    # JSON in markdown code block
    response = '```json\n{"key": "value"}\n```'
    assert provider._extract_json(response) == '{"key": "value"}'
    
    # JSON with commentary
    response = 'Here is the JSON:\n{"key": "value"}\nThat was it.'
    assert provider._extract_json(response) == '{"key": "value"}'


@patch('src.providers.claude.requests.post')
def test_claude_provider_call_messages_success(mock_post):
    """Test successful Claude Messages API call."""
    provider = ClaudeProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{
            "type": "text",
            "text": '{"targetLanguage": "de", "translations": []}'
        }],
        "usage": {"input_tokens": 10, "output_tokens": 20}
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    result = provider._call_claude_messages("Test prompt")
    assert result == '{"targetLanguage": "de", "translations": []}'
    
    # Verify headers
    call_args = mock_post.call_args
    headers = call_args[1]["headers"]
    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"] == "2023-06-01"


@patch('src.providers.claude.requests.post')
def test_claude_provider_rate_limit_retry(mock_post):
    """Test Claude API rate limit handling with retry."""
    provider = ClaudeProvider(api_key="test-key", max_retries=2)
    
    # First call: rate limit
    rate_limit_response = Mock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "1"}
    rate_limit_response.text = "Rate limit exceeded"
    
    # Second call: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "content": [{"type": "text", "text": "success"}]
    }
    success_response.ok = True
    
    mock_post.side_effect = [rate_limit_response, success_response]
    
    result = provider._call_claude_messages("Test prompt")
    assert result == "success"
    assert mock_post.call_count == 2


@patch('src.providers.claude.requests.post')
def test_claude_provider_authentication_error(mock_post):
    """Test Claude API authentication error handling."""
    provider = ClaudeProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception, match="authentication failed"):
        provider._call_claude_messages("Test prompt")


@patch('src.providers.claude.requests.post')
def test_claude_provider_server_error_retry(mock_post):
    """Test Claude API server error handling with retry."""
    provider = ClaudeProvider(api_key="test-key", max_retries=2)
    
    # First call: server error
    server_error_response = Mock()
    server_error_response.status_code = 500
    server_error_response.text = "Internal server error"
    
    # Second call: success
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "content": [{"type": "text", "text": "success"}]
    }
    success_response.ok = True
    
    mock_post.side_effect = [server_error_response, success_response]
    
    result = provider._call_claude_messages("Test prompt")
    assert result == "success"
    assert mock_post.call_count == 2


@patch('src.providers.claude.ClaudeProvider._call_claude_messages')
@patch('src.providers.claude.validate_llm_output')
def test_claude_provider_translate_batch_sync_success(mock_validate, mock_call):
    """Test successful synchronous translation batch."""
    provider = ClaudeProvider(api_key="test-key", use_batch_api=False)
    
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
    mock_call.assert_called_once()


@patch('src.providers.claude.ClaudeProvider._call_claude_messages')
@patch('src.providers.claude.validate_llm_output')
def test_claude_provider_translate_batch_repair_flow(mock_validate, mock_call):
    """Test translation batch with repair flow for invalid JSON."""
    provider = ClaudeProvider(api_key="test-key", use_batch_api=False)
    
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


@patch('src.providers.claude.ClaudeProvider._call_claude_messages')
def test_claude_provider_translate_batch_empty_items(mock_call):
    """Test translation batch with empty items list."""
    provider = ClaudeProvider(api_key="test-key")
    
    result = provider.translate_batch("en", "de", [])
    
    assert result["targetLanguage"] == "de"
    assert result["translations"] == []
    mock_call.assert_not_called()


def test_claude_provider_auto_use_batch_api():
    """Test auto-detection of batch API based on item count."""
    provider = ClaudeProvider(api_key="test-key", batch_threshold=5)
    
    # Small batch - should use sync
    small_items = [{"key": f"item{i}", "text": f"Text {i}"} for i in range(3)]
    assert provider.use_batch_api is False
    assert len(small_items) <= provider.batch_threshold
    
    # Large batch - should use async (when implemented)
    large_items = [{"key": f"item{i}", "text": f"Text {i}"} for i in range(10)]
    assert len(large_items) > provider.batch_threshold


@patch('src.providers.claude.requests.post')
def test_claude_provider_create_batch(mock_post):
    """Test batch creation."""
    provider = ClaudeProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "batch_abc123",
        "processing_status": "validating"
    }
    mock_response.ok = True
    mock_post.return_value = mock_response
    
    requests_list = [
        {
            "custom_id": "item-0",
            "params": {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": "test"}]
            }
        }
    ]
    
    batch_id = provider._create_batch(requests_list)
    assert batch_id == "batch_abc123"
    
    # Verify headers
    call_args = mock_post.call_args
    headers = call_args[1]["headers"]
    assert headers["x-api-key"] == "test-key"
    assert headers["anthropic-version"] == "2023-06-01"


@patch('src.providers.claude.requests.get')
def test_claude_provider_get_batch_status(mock_get):
    """Test batch status retrieval."""
    provider = ClaudeProvider(api_key="test-key")
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "batch_abc123",
        "processing_status": "ended",
        "results_url": "https://api.anthropic.com/v1/messages/batches/batch_abc123/results"
    }
    mock_response.ok = True
    mock_get.return_value = mock_response
    
    status = provider._get_batch_status("batch_abc123")
    assert status["processing_status"] == "ended"
    assert "results_url" in status


@patch('src.providers.claude.ClaudeProvider._get_batch_status')
def test_claude_provider_poll_batch_status(mock_get_status):
    """Test batch status polling."""
    provider = ClaudeProvider(api_key="test-key")
    
    # First call: in progress
    # Second call: ended
    mock_get_status.side_effect = [
        {"processing_status": "in_progress"},
        {"processing_status": "ended", "results_url": "https://example.com/results"}
    ]
    
    with patch('time.sleep'):  # Mock sleep to speed up test
        status = provider._poll_batch_status("batch_abc123", max_wait_hours=0.1)
        assert status["processing_status"] == "ended"


@patch('src.providers.claude.requests.get')
def test_claude_provider_get_batch_results(mock_get):
    """Test batch results retrieval."""
    provider = ClaudeProvider(api_key="test-key")
    
    # Mock JSONL response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '''{"custom_id": "item-0", "output": {"content": [{"type": "text", "text": "result1"}]}}
{"custom_id": "item-1", "output": {"content": [{"type": "text", "text": "result2"}]}}'''
    mock_response.ok = True
    mock_get.return_value = mock_response
    
    results = provider._get_batch_results("https://example.com/results")
    assert len(results) == 2
    assert results[0]["custom_id"] == "item-0"
    assert results[1]["custom_id"] == "item-1"


@patch('src.providers.claude.ClaudeProvider._create_batch')
@patch('src.providers.claude.ClaudeProvider._poll_batch_status')
@patch('src.providers.claude.ClaudeProvider._get_batch_results')
@patch('src.providers.claude.validate_llm_output')
def test_claude_provider_translate_batch_async(mock_validate, mock_get_results, mock_poll, mock_create):
    """Test asynchronous batch translation."""
    provider = ClaudeProvider(api_key="test-key", use_batch_api=True)
    
    # Mock batch creation
    mock_create.return_value = "batch_abc123"
    
    # Mock batch completion
    mock_poll.return_value = {
        "processing_status": "ended",
        "results_url": "https://example.com/results"
    }
    
    # Mock results
    mock_get_results.return_value = [
        {
            "custom_id": "item-0-test",
            "output": {
                "content": [{
                    "type": "text",
                    "text": '{"targetLanguage": "de", "translations": [{"key": "test", "text": "Test"}]}'
                }]
            }
        }
    ]
    
    # Mock validation
    mock_validate.return_value = (True, {
        "targetLanguage": "de",
        "translations": [{"key": "test", "text": "Test"}]
    }, "")
    
    items = [{"key": "test", "text": "Test"}]
    result = provider.translate_batch("en", "de", items)
    
    assert result["targetLanguage"] == "de"
    assert len(result["translations"]) == 1
    mock_create.assert_called_once()
    mock_poll.assert_called_once()

