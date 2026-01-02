# Verification Guide: Testing Without Real API Keys

This guide explains how to verify the application works correctly without using real API keys.

## Overview

The application uses **mocked HTTP requests** in tests, so you can verify almost everything without real API keys. Only the actual LLM translation quality requires real API calls.

## What Can Be Verified Without API Keys

### ✅ Fully Testable (No API Keys Needed)

1. **Provider Initialization**
   - Environment variable reading
   - Parameter validation
   - Default value handling
   - Error handling for missing keys

2. **Request Construction**
   - API endpoint URLs
   - Headers (Authorization, Content-Type, etc.)
   - Request payload format
   - Model selection
   - Temperature settings

3. **Response Parsing**
   - JSON extraction from markdown
   - Response format handling
   - Content extraction (OpenAI vs Anthropic formats)
   - Error response parsing

4. **Error Handling**
   - Rate limit (429) retry logic
   - Authentication errors (401)
   - Permission errors (403)
   - Server errors (500, 502, 503)
   - Timeout handling
   - Exponential backoff

5. **JSON Repair Flow**
   - Invalid JSON detection
   - Repair prompt generation
   - Retry logic (max 2 attempts)

6. **Protected Token Preservation**
   - Token extraction
   - Token validation
   - Escaping fixes

7. **Validation Logic**
   - Schema validation
   - Placeholder signature matching
   - Empty value detection

8. **File I/O**
   - Reading i18n files (folder and explicit)
   - Writing memory.jsonl
   - Merging translations
   - Flattening/unflattening JSON

9. **CLI Integration**
   - Argument parsing
   - Provider selection
   - Flag handling
   - Error messages

10. **Batch Processing (Claude)**
    - Batch creation
    - Status polling
    - Results retrieval
    - JSONL parsing

### ⚠️ Requires Real API Keys (Limited Testing)

1. **Actual Translation Quality**
   - Translation accuracy
   - Context understanding
   - Tone preservation

2. **Real API Rate Limits**
   - Actual rate limit behavior
   - Real retry-after headers

3. **Cost Verification**
   - Actual token usage
   - Batch API cost savings

## Running Tests

### Run All Tests

```bash
# Run all tests (no API keys needed)
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_openai_provider.py -v

# Run specific test
pytest tests/test_openai_provider.py::test_openai_provider_init_from_env -v
```

### Test Coverage

```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Structure

### Provider Tests

All provider tests use `unittest.mock` to mock HTTP requests:

```python
@patch('src.providers.openai.requests.post')
def test_openai_provider_call_success(mock_post):
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "..."}}]
    }
    mock_post.return_value = mock_response
    
    # Test provider
    provider = OpenAIProvider(api_key="test-key")
    result = provider._call_openai("prompt")
    
    # Verify result
    assert result == "..."
```

### What Gets Mocked

- **HTTP Requests**: All `requests.post()` and `requests.get()` calls
- **Time Delays**: `time.sleep()` is mocked to speed up tests
- **Environment Variables**: `os.getenv()` is patched with test values

### What Gets Tested

- **Request Format**: Headers, payload structure, URLs
- **Response Handling**: Parsing, error detection, retry logic
- **Business Logic**: Translation flow, validation, repair

## Manual Verification Steps

### 1. Test Provider Initialization

```bash
# Test OpenAI provider (should fail without key, but show clear error)
python -m src.cli translate-missing \
  --target-lang en \
  --provider openai \
  --memory-file work/memory.jsonl

# Expected: Clear error message about missing API key
```

### 2. Test Request Construction

You can add debug logging to see request format:

```python
# In provider code, add:
import logging
logging.basicConfig(level=logging.DEBUG)
logger.debug(f"Request URL: {url}")
logger.debug(f"Request headers: {headers}")
logger.debug(f"Request payload: {payload}")
```

### 3. Test File I/O

```bash
# Test build-memory (no API needed)
python -m src.cli build-memory \
  --i18n-dir example/set1 \
  --source-lang en \
  --output work/test-memory.jsonl

# Verify output
cat work/test-memory.jsonl
```

### 4. Test Validation

```bash
# Create a test response file
cat > test-response.json << 'EOF'
{
  "targetLanguage": "fr",
  "translations": [
    {"key": "welcome", "text": "Bienvenue"}
  ]
}
EOF

# Validate it
python -m src.cli validate test-response.json
```

### 5. Test Merge Logic

```bash
# Build memory
python -m src.cli build-memory --i18n-dir example/set1 --source-lang en

# Manually edit memory.jsonl to add a translation
# Then test write-back
python -m src.cli write-back \
  --memory-file work/memory.jsonl \
  --target-lang fr \
  --i18n-dir example/set1
```

## Integration Testing (Mocked Providers)

You can create integration tests that use mocked providers:

```python
@patch('src.providers.openai.requests.post')
def test_full_translation_flow(mock_post):
    # Mock provider responses
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {
            "choices": [{
                "message": {"content": '{"targetLanguage": "fr", "translations": [...]}'}
            }]
        },
        ok=True
    )
    
    # Run full flow
    # build-memory -> translate-missing -> write-back
    # All without real API calls
```

## Verification Checklist

### Core Functionality ✅
- [x] Provider initialization (all providers)
- [x] Request construction (headers, payloads)
- [x] Response parsing (all formats)
- [x] Error handling (all error types)
- [x] Retry logic (exponential backoff)
- [x] JSON repair flow
- [x] Protected token preservation

### File Operations ✅
- [x] Reading i18n files (folder mode)
- [x] Reading i18n files (file mode)
- [x] Building memory.jsonl
- [x] Merging translations
- [x] Writing output files

### CLI Integration ✅
- [x] Argument parsing
- [x] Provider selection
- [x] Flag validation
- [x] Error messages

### Batch Processing (Claude) ✅
- [x] Batch creation
- [x] Status polling
- [x] Results retrieval
- [x] Auto-detection logic

## What Requires Real API Keys

Only these require actual API calls:

1. **Translation Quality**: Actual translation accuracy
2. **Real Rate Limits**: Actual API rate limit behavior
3. **Cost Verification**: Real token usage and costs
4. **Batch API Timing**: Actual batch processing times

## Recommendations

1. **Run Full Test Suite**: `pytest -v` to verify all mocked functionality
2. **Test File Operations**: Use example files to test I/O without APIs
3. **Manual CLI Testing**: Test CLI with invalid keys to verify error messages
4. **Integration Tests**: Create end-to-end tests with mocked providers
5. **Real API Testing**: Only test with real keys for final quality verification

## Example: Full Flow Test (Mocked)

```python
def test_full_flow_with_mocked_provider(tmp_path):
    """Test complete flow: build-memory -> translate -> write-back"""
    
    # Setup test files
    i18n_dir = tmp_path / "i18n"
    i18n_dir.mkdir()
    (i18n_dir / "en.json").write_text('{"welcome": "Welcome"}')
    (i18n_dir / "fr.json").write_text('{"welcome": null}')
    
    # Build memory
    memory_file = tmp_path / "memory.jsonl"
    build_memory(output_file=memory_file, source_lang="en", i18n_dir=i18n_dir)
    
    # Mock provider
    with patch('src.providers.openai.requests.post') as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": '{"targetLanguage": "fr", "translations": [{"key": "welcome", "text": "Bienvenue"}]}'
                    }
                }]
            },
            ok=True
        )
        
        # Translate
        provider = OpenAIProvider(api_key="test-key")
        items = [{"key": "welcome", "text": "Welcome"}]
        result = provider.translate_batch("en", "fr", items)
        
        # Verify
        assert result["targetLanguage"] == "fr"
        assert result["translations"][0]["text"] == "Bienvenue"
```

## Summary

**You can verify ~95% of functionality without real API keys** using:
- Unit tests with mocked HTTP requests
- File I/O tests with example data
- CLI tests with invalid keys (error handling)
- Integration tests with mocked providers

Only translation quality and real API behavior require actual API keys.

