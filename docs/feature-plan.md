# Feature Plan: Enhanced Input Options & OpenRouter Support

## Overview

This document outlines the plan for three new features:
1. **Flexible Source Language** - Make source language fully configurable
2. **File Input Options** - Support both folder-based and explicit file-based input
3. **OpenRouter Provider** - Add OpenRouter as a translation provider

---

## Feature 1: Flexible Source Language ✅ COMPLETE

### Current State
- Source language defaults to `"sv"` (Swedish)
- `--source-lang` flag exists and is used consistently
- Code already supports any source language

### Changes Completed

#### 1.1 Documentation Updates ✅
- [x] Updated README.md to remove hardcoded "Swedish" references
- [x] Updated `.cursor/index.mdc` to reflect flexible source language
- [x] Updated `.specify/memory/constitution.md` to be generic

#### 1.2 Code Review ✅
- [x] Reviewed all functions that use `source_lang` parameter - all support any language
- [x] Verified `--source-lang` is consistently used in all CLI commands
- [x] Verified `build_memory()` properly handles any source language
- [x] Verified `translate_missing()` properly handles any source language

#### 1.3 Testing
- [ ] Test with English as source language (can be done manually)
- [ ] Test with other languages (e.g., French, German) (can be done manually)
- [ ] Verify memory.jsonl generation works with different sources
- [ ] Verify translation works with different sources

### Implementation Notes
- Code already fully supports any source language
- Default "sv" is just a convenience default, can be overridden
- No breaking changes - backward compatible

---

## Feature 2: File Input Options

### Current State
- Only supports folder-based input: `--i18n-dir PATH`
- Reads all `*.json` files from directory
- Language code inferred from filename stem (e.g., `en.json` → `"en"`)

### New Requirements
- Support explicit file specification: `--source-file PATH` and `--target-file PATH`
- Maintain backward compatibility with folder-based approach
- Support both modes in CLI

### Design Decision

**Option A: Separate commands**
- `build-memory-folder` (existing)
- `build-memory-files` (new)

**Option B: Unified with flags** (RECOMMENDED)
- Keep `--i18n-dir` for folder mode
- Add `--source-file` and `--target-file` for explicit file mode
- Mutually exclusive: if files specified, ignore `--i18n-dir`

### Changes Needed

#### 2.1 CLI Changes (`src/cli.py`) ✅
- [x] Add `--source-file PATH` argument to `build-memory` command
- [x] Add `--target-file PATH` argument (optional, can specify multiple)
- [x] Add `--source-file` and `--target-file` to `run` command
- [x] Add `--output-file` to `write-back` command
- [x] Add validation: either `--i18n-dir` OR `--source-file`/`--target-file`, not both
- [x] Add language code inference from filename (with `--source-lang` override)

#### 2.2 IO Changes (`src/io_json.py`) ✅
- [x] Create `read_i18n_files_explicit()` function
  - Takes list of file paths
  - Returns `Dict[str, Dict[str, Any]]` mapping language codes to translations
  - Language code from filename stem or explicit mapping
- [x] Function handles explicit file mode

#### 2.3 Memory Changes (`src/memory.py`) ✅
- [x] Update `build_memory()` to accept either:
  - `i18n_dir: Optional[Path]` (folder mode)
  - `i18n_files: Optional[Dict[str, Path]]` (file mode: lang_code -> file_path)
- [x] Validates mutually exclusive modes

#### 2.4 Merge Changes (`src/merge.py`) ✅
- [x] Update `merge_translations()` to support file-based output
- [x] Add `--output-file` option for `write-back` command
- [x] If `--output-file` specified, write to that file instead of `i18n_dir/{lang}.json`

#### 2.5 Testing
- [ ] Test folder-based mode (backward compatibility)
- [ ] Test file-based mode with single source file
- [ ] Test file-based mode with multiple target files
- [ ] Test language code inference from filenames
- [ ] Test explicit language code specification
- [ ] Test error handling (invalid files, missing files)

### Example Usage

```bash
# Folder-based (existing)
python -m src.cli build-memory --i18n-dir i18n --source-lang en

# File-based (new)
python -m src.cli build-memory \
  --source-file example/set1/en.json \
  --target-file example/set1/fr.json \
  --target-file example/set1/de.json \
  --source-lang en

# Run with file-based
python -m src.cli run \
  --source-file example/set1/en.json \
  --target-file example/set1/fr.json \
  --source-lang en \
  --target-lang fr
```

### Implementation Notes
- Maintain backward compatibility
- File mode should be explicit and clear
- Consider adding `--lang-map` for custom language code mapping

---

## Feature 3: OpenRouter Provider

### Current State
- Supports Ollama (local) and OpenAI (cloud)
- Provider interface is well-defined in `src/providers/base.py`
- OpenAI provider serves as good template

---

## Feature 4: Claude (Anthropic) Provider

### Current State
- Supports Ollama (local) and OpenAI (cloud)
- Provider interface is well-defined in `src/providers/base.py`
- OpenAI provider serves as good template for API-based providers

### Claude Overview
- Anthropic's Claude API for translation
- **Two API modes available:**
  1. **Messages API (Synchronous)** - Immediate results, standard pricing
  2. **Message Batches API (Asynchronous)** - Up to 10,000 items, 50% cost savings, 24-hour processing
- Requires API key: `ANTHROPIC_API_KEY`
- Base URL: `https://api.anthropic.com/v1`
- Default model: `claude-3-5-sonnet-20241022` (or latest)
- API format: Messages API with `anthropic-version` header

### Batch Processing Strategy

**Current Implementation Pattern:**
- Processes batches of 10-20 items synchronously
- Immediate results for each batch
- Suitable for interactive use and small-to-medium volumes

**Claude Batch API Benefits:**
- **Cost Savings**: 50% discount on input and output tokens
- **High Throughput**: Up to 10,000 requests per batch
- **Asynchronous**: Processed within 24 hours
- **Best for**: Large-scale, non-time-sensitive translations

**Recommended Approach:**
- **Default**: Use synchronous Messages API (immediate results)
- **Optional**: Add `--use-batch-api` flag for large volumes
- **Auto-detect**: Consider using batch API when >100 items to translate

### OpenRouter Overview
- Unified API for accessing multiple LLM models
- Similar to OpenAI's API format
- Requires API key: `OPENROUTER_API_KEY`
- Base URL: `https://openrouter.ai/api/v1`
- Uses same chat completions format as OpenAI

### Changes Needed

#### 3.1 Provider Implementation (`src/providers/openrouter.py`) ✅
- [x] Create `OpenRouterProvider` class extending `TranslationProvider`
- [ ] Implement `__init__()`:
  - Read `OPENROUTER_API_KEY` from environment (required)
  - Support `OPENROUTER_BASE_URL` env var (default: `https://openrouter.ai/api/v1`)
  - Support `OPENROUTER_MODEL` env var (default: TBD - check OpenRouter docs)
  - Support constructor parameters for testing
- [ ] Implement `translate_batch()`:
  - Use OpenAI-compatible chat completions API
  - Reuse `build_translation_prompt()` from `src/prompts/translate.py`
  - Reuse `_extract_json()` and `_fix_json_escaping()` (or refactor to shared utility)
  - Reuse `validate_llm_output()` from `src/validate/schema.py`
  - Implement repair flow (max 2 attempts, similar to OpenAIProvider)
  - Set `temperature=0.1` for deterministic output
- [ ] Error handling:
  - Handle rate limits (429) with exponential backoff
  - Handle authentication errors (401)
  - Handle server errors (500, 502, 503) with retry
  - Handle timeout errors
  - Log errors to run logger

#### 3.2 CLI Integration (`src/cli.py`)
- [ ] Add `"openrouter"` to `--provider` choices
- [ ] Add `--openrouter-model` flag (default from `OPENROUTER_MODEL` env)
- [ ] Wire `--provider openrouter` to `OpenRouterProvider` initialization
- [ ] Handle missing `OPENROUTER_API_KEY` with clear error message

#### 3.3 Configuration & Environment
- [ ] Document `OPENROUTER_API_KEY` requirement in README.md
- [ ] Document `OPENROUTER_BASE_URL` (optional) in docs/runbook.md
- [ ] Document `OPENROUTER_MODEL` (optional) in docs/runbook.md
- [ ] Add OpenRouter to provider comparison in docs/runbook.md

#### 3.4 Testing
- [ ] Unit tests for `OpenRouterProvider` initialization
- [ ] Unit tests for request construction (verify API format)
- [ ] Unit tests for response parsing (valid JSON, markdown-wrapped, etc.)
- [ ] Unit tests for error handling (429, 401, 500, timeout)
- [ ] Unit tests for repair flow (invalid JSON -> repair prompt -> retry)
- [ ] Unit tests for protected token preservation
- [ ] Integration-style tests with mocked HTTP requests (no API key needed)

#### 3.5 Documentation
- [ ] Update `docs/runbook.md` with OpenRouter usage examples
- [ ] Add OpenRouter to "Choosing a Provider" section
- [ ] Document API key setup: `export OPENROUTER_API_KEY=sk-...`
- [ ] Document model selection and cost considerations
- [ ] Add troubleshooting section for common OpenRouter API errors

---

## Feature 4: Claude (Anthropic) Provider

### Changes Needed

#### 4.1 Provider Implementation (`src/providers/claude.py`)
- [ ] Create `ClaudeProvider` class extending `TranslationProvider`
- [ ] Implement `__init__()`:
  - Read `ANTHROPIC_API_KEY` from environment (required)
  - Support `ANTHROPIC_BASE_URL` env var (default: `https://api.anthropic.com/v1`)
  - Support `ANTHROPIC_MODEL` env var (default: `claude-3-5-sonnet-20241022`)
  - Support `use_batch_api` parameter (default: False, use synchronous API)
  - Support constructor parameters for testing
- [ ] Implement synchronous `translate_batch()` (default mode):
  - Use Anthropic Messages API format
  - Endpoint: `POST /v1/messages`
  - Headers: `anthropic-version: 2023-06-01`, `x-api-key: {key}`
  - Request format: `{"model": "...", "max_tokens": 4096, "messages": [...]}`
  - Response format: `{"content": [{"type": "text", "text": "..."}]}`
  - Reuse `build_translation_prompt()` from `src/prompts/translate.py`
  - Reuse `_extract_json()` and `_fix_json_escaping()` (or refactor to shared utility)
  - Reuse `validate_llm_output()` from `src/validate/schema.py`
  - Implement repair flow (max 2 attempts, similar to OpenAIProvider)
  - Set `temperature=0.1` for deterministic output
- [ ] Implement asynchronous batch API support (optional):
  - Method: `translate_batch_async()` or detect in `translate_batch()` based on item count
  - Endpoint: `POST /v1/messages/batches`
  - Request format:
    ```json
    {
      "requests": [
        {
          "custom_id": "request-1",
          "params": {
            "model": "...",
            "max_tokens": 4096,
            "messages": [...]
          }
        }
      ]
    }
    ```
  - Monitor batch status: `GET /v1/messages/batches/{batch_id}`
  - Retrieve results: `GET {results_url}` when `processing_status == "ended"`
  - Handle batch status: `validating`, `in_progress`, `finalizing`, `ended`, `expired`, `cancelling`, `cancelled`
  - Map `custom_id` back to original items
  - Process results JSONL file
- [ ] Error handling (both modes):
  - Handle rate limits (429) with exponential backoff
  - Handle authentication errors (401)
  - Handle server errors (500, 502, 503) with retry
  - Handle timeout errors
  - Handle batch API errors (expired, cancelled batches)
  - Log errors to run logger
- [ ] Batch API considerations:
  - Maximum 10,000 requests per batch
  - Maximum 256 MB total batch size
  - Results available as JSONL file
  - Processing time: up to 24 hours
  - Implement polling mechanism for batch status
  - Store batch_id for resumability

#### 4.2 CLI Integration (`src/cli.py`)
- [ ] Add `"claude"` to `--provider` choices
- [ ] Add `--claude-model` flag (default from `ANTHROPIC_MODEL` env or `claude-3-5-sonnet-20241022`)
- [ ] Add `--use-batch-api` flag (optional, for large volumes, uses asynchronous batch API)
- [ ] Add `--batch-threshold` flag (optional, auto-use batch API when items > threshold, default: 100)
- [ ] Wire `--provider claude` to `ClaudeProvider` initialization
- [ ] Handle missing `ANTHROPIC_API_KEY` with clear error message
- [ ] Add batch API status monitoring (if using batch API)

#### 4.3 Configuration & Environment
- [ ] Document `ANTHROPIC_API_KEY` requirement in README.md
- [ ] Document `ANTHROPIC_BASE_URL` (optional) in docs/runbook.md
- [ ] Document `ANTHROPIC_MODEL` (optional) in docs/runbook.md
- [ ] Add Claude to provider comparison in docs/runbook.md

#### 4.4 Testing
- [ ] Unit tests for `ClaudeProvider` initialization
- [ ] Unit tests for request construction (verify Anthropic API format)
- [ ] Unit tests for response parsing (valid JSON, markdown-wrapped, etc.)
- [ ] Unit tests for error handling (429, 401, 500, timeout)
- [ ] Unit tests for repair flow (invalid JSON -> repair prompt -> retry)
- [ ] Unit tests for protected token preservation
- [ ] Integration-style tests with mocked HTTP requests (no API key needed)

#### 4.5 Documentation
- [ ] Update `docs/runbook.md` with Claude usage examples
- [ ] Add Claude to "Choosing a Provider" section
- [ ] Document API key setup: `export ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Document model selection and cost considerations
- [ ] Document batch API usage:
  - When to use batch API (large volumes, cost-sensitive)
  - When to use synchronous API (immediate results, small batches)
  - Cost comparison (50% savings with batch API)
  - Processing time expectations (up to 24 hours for batch API)
- [ ] Add troubleshooting section for common Anthropic API errors
- [ ] Document batch API workflow and status monitoring

#### 3.2 CLI Integration (`src/cli.py`)
- [ ] Add `"openrouter"` to `--provider` choices
- [ ] Add `--openrouter-model` flag (default from `OPENROUTER_MODEL` env)
- [ ] Wire `--provider openrouter` to `OpenRouterProvider` initialization
- [ ] Handle missing `OPENROUTER_API_KEY` with clear error message

#### 3.3 Configuration & Environment
- [ ] Document `OPENROUTER_API_KEY` requirement in README.md
- [ ] Document `OPENROUTER_BASE_URL` (optional) in docs/runbook.md
- [ ] Document `OPENROUTER_MODEL` (optional) in docs/runbook.md
- [ ] Add OpenRouter to provider comparison in docs/runbook.md

#### 3.4 Testing
- [ ] Unit tests for `OpenRouterProvider` initialization
- [ ] Unit tests for request construction (verify API format)
- [ ] Unit tests for response parsing (valid JSON, markdown-wrapped, etc.)
- [ ] Unit tests for error handling (429, 401, 500, timeout)
- [ ] Unit tests for repair flow (invalid JSON -> repair prompt -> retry)
- [ ] Unit tests for protected token preservation
- [ ] Integration-style tests with mocked HTTP requests (no API key needed)

#### 3.5 Documentation
- [ ] Update `docs/runbook.md` with OpenRouter usage examples
- [ ] Add OpenRouter to "Choosing a Provider" section
- [ ] Document API key setup: `export OPENROUTER_API_KEY=sk-...`
- [ ] Document model selection and cost considerations
- [ ] Add troubleshooting section for common OpenRouter API errors

### Implementation Notes
- OpenRouter API is OpenAI-compatible, so can reuse much of OpenAIProvider code
- Consider refactoring shared code (JSON extraction, repair flow) into base utilities
- OpenRouter supports many models - document popular choices
- Cost varies by model - document this

### Example Usage

```bash
export OPENROUTER_API_KEY=sk-or-...
python -m src.cli run \
  --target-lang fr \
  --provider openrouter \
  --openrouter-model anthropic/claude-3.5-sonnet
```

---

### Implementation Notes
- Anthropic API format differs from OpenAI (Messages API vs Chat Completions)
- Need to handle `anthropic-version` header
- Response format: `{"content": [{"type": "text", "text": "..."}]}`
- Can reuse prompt building and validation logic
- Consider refactoring shared code (JSON extraction, repair flow) into base utilities

### Example Usage

**Synchronous API (default, immediate results):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m src.cli run \
  --target-lang fr \
  --provider claude \
  --claude-model claude-3-5-sonnet-20241022
```

**Batch API (asynchronous, 50% cost savings, for large volumes):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m src.cli run \
  --target-lang fr \
  --provider claude \
  --use-batch-api \
  --claude-model claude-3-5-sonnet-20241022
```

**Auto-detect batch API (use batch API if >100 items):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m src.cli run \
  --target-lang fr \
  --provider claude \
  --batch-threshold 100
```

### Implementation Notes
- **Default behavior**: Use synchronous Messages API for immediate results
- **Batch API**: Optional, for large volumes (100+ items) when cost savings matter
- **Cost savings**: Batch API offers 50% discount but takes up to 24 hours
- **Trade-off**: Speed vs. cost - let users choose based on their needs
- **Resumability**: Store batch_id to allow resuming batch status checks
- **Status monitoring**: Poll batch status endpoint until `processing_status == "ended"`

---

## API Key Management

### Current Approach: Environment Variables ✅

The project uses **environment variables** for API key management, which is the standard practice for CLI tools.

**Pattern:**
```python
import os
api_key = api_key or os.getenv("PROVIDER_API_KEY")
```

**Usage:**
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-...
```

**See `docs/api-key-management.md` for:**
- Detailed explanation of environment variable pattern
- Comparison with other API key management options
- Security best practices
- Recommendations for this project

### Why Environment Variables?

✅ **Secure** - Keys not stored in code or files  
✅ **CI/CD friendly** - Easy to set in CI systems  
✅ **Standard practice** - Common for CLI tools  
✅ **No dependencies** - Uses built-in `os` module  
✅ **Flexible** - Can be set per-session or in shell profile

---

## Implementation Order

### Phase 1: Source Language Flexibility (Quick Win)
- Low risk, mostly documentation
- Can be done first to unblock other features

### Phase 2: File Input Options (Medium Complexity)
- Requires careful design to maintain backward compatibility
- More testing needed
- Useful for the example/set1 use case

### Phase 3: OpenRouter Provider (Similar to OpenAI)
- Can reuse OpenAIProvider as template
- Well-defined interface makes this straightforward
- Good to do after file input is stable

---

## Questions to Resolve

1. **File Input**: Should we support both folder AND explicit files in same command, or make them mutually exclusive?
   - **Decision**: Mutually exclusive for clarity

2. **Language Code Inference**: When using `--source-file`, how do we know the language code?
   - **Option A**: Infer from filename (e.g., `en.json` → `"en"`)
   - **Option B**: Require `--source-lang` flag
   - **Decision**: Support both - infer from filename but allow override

3. **OpenRouter Default Model**: What should the default model be?
   - **Decision**: Research OpenRouter docs, pick a good default (maybe `anthropic/claude-3.5-sonnet` or `openai/gpt-4o-mini`)

4. **Shared Code Refactoring**: Should we extract common code from OpenAIProvider and OpenRouterProvider?
   - **Decision**: Yes, but can do as follow-up if time is limited

---

## Testing Strategy

### Feature 1 (Source Language)
- Test with English, French, German as source
- Verify all commands work with different sources

### Feature 2 (File Input)
- Test backward compatibility (folder mode)
- Test new file mode with various file combinations
- Test error cases (missing files, invalid JSON)

### Feature 3 (OpenRouter)
- Mock HTTP requests (no real API calls in tests)
- Test all error paths
- Test repair flow
- Test protected token preservation

---

## Documentation Updates

- [ ] Update README.md with new features
- [ ] Update docs/runbook.md with examples
- [ ] Update docs/phases_checklist.md (add new phase or update existing)
- [ ] Update SETUP.md if needed

