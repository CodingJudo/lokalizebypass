# i18n LLM Translator (file-only)

A small, repeatable pipeline that translates missing i18n strings using LLM providers.

## Goal

- Reads existing i18n JSON files (sv + 13 target languages)
- Translates ONLY missing strings in target languages using an LLM provider
- Validates output (format + placeholders) deterministically
- Writes updated i18n JSON files without overwriting existing translations

## Non-negotiable constraints

- Never overwrite an existing non-empty translation unless an explicit "force" flag is passed.
- Swedish (sv) is the single source of truth.
- Preserve placeholders exactly (e.g. {name}, {{name}}, %s, ICU patterns).
- LLM output must be machine-parseable JSON (no prose).
- The pipeline must be resumable and idempotent using files only.

## Phase 1: Memory artifact + IO

Currently implemented:
- `build-memory`: Generate work/memory.jsonl from i18n/*.json
- Missing detection per language
- Placeholder signature generation

## Usage

```bash
# Build memory artifact from i18n files
python -m src.cli build-memory
```

## Development

```bash
# Run tests
pytest

# Install in development mode
pip install -e .
```

