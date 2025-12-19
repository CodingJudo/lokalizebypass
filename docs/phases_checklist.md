# Phases checklist: i18n LLM Translator (file-only)

## Phase 0: Repo skeleton
- [x] Create folder structure (src/, docs/, work/, i18n/)
- [x] Add Cursor rules files (.cursor/index.mdc + .cursor/rules/*.mdc)
- [x] Add Spec Kit constitution (.specify/memory/constitution.md)
- [x] Add minimal README + runbook stub

## Phase 1: Memory artifact + IO
- [x] Read per-language JSON files into memory
- [x] Implement `build-memory`: generate work/memory.jsonl from i18n/*.json
- [x] Implement missing detection per language
- [x] Tests: missing detection, stable key handling

## Phase 2: Validation core
- [x] Implement placeholder extraction + signature
- [x] Implement JSON schema validation for LLM output
- [x] Implement merge-only-missing logic for i18n output files
- [x] Tests: placeholder mismatch fails; merge does not overwrite

## Phase 3: Providers + translation loop
- [x] Implement provider interface `translate_batch(...)`
- [x] Implement Ollama provider (local)
- [x] Implement API provider skeleton (env config, retries, rate limiting)
- [x] Implement batching strategy (by namespace/prefix; stable ordering)
- [x] Implement repair flow for invalid JSON
- [x] Per-run logs: work/runs/<run_id>/

## Phase 4: End-to-end + reporting
- [x] Implement `run`: build-memory -> translate-missing -> validate -> write-back
- [x] Add summary report (missing before/after, invalid, needs_review)
- [x] Ensure reruns are idempotent (no churn)
- [x] Document usage in docs/runbook.md

## Phase 5: Optional hardening
- [ ] Glossary + do-not-translate support
- [ ] Stale detection when sv changes (needs_review flag)
- [ ] CI step: validate placeholders + schema without calling LLM

## Phase 6: OpenAI Provider Support
- [x] Implement `OpenAIProvider` in `src/providers/openai.py`
  - [x] Use OpenAI Chat Completions API (`POST /v1/chat/completions`)
  - [x] Convert prompt to chat messages format: `[{"role": "user", "content": prompt}]`
  - [x] Use `response_format={"type": "json_object"}` if supported (JSON mode)
  - [x] Map `translate_batch(...)` parameters to OpenAI API request
  - [x] Extract `content` from `choices[0].message.content` in response
  - [x] Reuse `build_translation_prompt()` for prompt generation
  - [x] Reuse `_extract_json()` and `_fix_json_escaping()` from OllamaProvider (or refactor to shared utility)
  - [x] Reuse `validate_llm_output()` for response validation
  - [x] Implement repair flow for invalid JSON (max 2 attempts, similar to OllamaProvider)
  - [x] Set `temperature=0.1` for deterministic output
- [x] Configuration & environment variables
  - [x] Read `OPENAI_API_KEY` from environment (required)
  - [x] Support `OPENAI_BASE_URL` env var (optional, default: `https://api.openai.com/v1`)
  - [x] Support `OPENAI_MODEL` env var (optional, default: `gpt-4o-mini`)
  - [x] Support constructor parameters: `api_key`, `base_url`, `model` (for testing/CLI)
  - [x] Document required env vars in README.md and docs/runbook.md
- [x] CLI integration
  - [x] Add `openai` to `--provider` choices in `src/cli.py`
  - [x] Add `--openai-model` flag (default from `OPENAI_MODEL` env or `gpt-4o-mini`)
  - [x] Wire `--provider openai` to `OpenAIProvider` initialization
  - [x] Handle missing `OPENAI_API_KEY` with clear error message
- [x] Error handling & rate limiting
  - [x] Handle rate limits (429 errors) with exponential backoff
  - [x] Handle authentication errors (401) with clear message about API key
  - [x] Handle permission errors (403) with clear error message
  - [x] Handle server errors (500, 502, 503) with retry logic
  - [x] Handle timeout errors with retry
  - [x] Log API errors to run logger (if provided)
- [x] Tests (all using mocked requests - no API key needed)
  - [x] Unit tests for `OpenAIProvider` initialization (with/without env vars)
  - [x] Unit tests for request construction (verify chat messages format, temperature, etc.)
  - [x] Unit tests for response parsing (valid JSON, markdown-wrapped, etc.)
  - [x] Unit tests for error handling (429, 401, 500, timeout)
  - [x] Unit tests for repair flow (invalid JSON -> repair prompt -> retry)
  - [x] Unit tests for protected token preservation (verify `\1`, `{{name}}` preserved)
  - [x] Integration-style tests with `responses` library or `unittest.mock` (mock HTTP requests)
  - [x] Test context support (global and per-key context in prompts)
- [x] Documentation
  - [x] Update `docs/runbook.md` with OpenAI usage examples
  - [x] Add "Choosing a Provider" section comparing Ollama vs OpenAI
  - [x] Document API key setup: `export OPENAI_API_KEY=sk-...`
  - [x] Document cost considerations (tokens per request, pricing)
  - [x] Add troubleshooting section for common OpenAI API errors
