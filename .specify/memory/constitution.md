# Constitution: i18n LLM Translator (file-only)

## Purpose
Translate missing i18n strings from a source language (configurable, default: sv) into target languages via LLMs while preserving existing translations and placeholder integrity.

## Invariants
- Never overwrite non-empty translations unless explicitly forced.
- The source language (configurable via --source-lang) is authoritative.
- Placeholders must be preserved exactly.
- LLM responses must be strict JSON matching the schema.
- The pipeline must be resumable and idempotent using files only.

## Tech choices
- Python pipeline runner.
- Canonical intermediate artifact: work/memory.jsonl.
- Provider abstraction: Ollama local; external API in production.

## Quality gates
- Placeholder validation is mandatory.
- Failures must be logged with enough data to replay the batch.
- Tests required for core invariants (placeholders, merge semantics, schema).
