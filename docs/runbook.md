# Runbook: i18n LLM Translator

## Overview

This runbook documents how to use the i18n LLM Translator pipeline.

## Phase 1: Building Memory Artifact

### Build Memory from i18n Files

Generate the canonical memory artifact (`work/memory.jsonl`) from your i18n JSON files:

```bash
python -m src.cli build-memory
```

Options:
- `--i18n-dir PATH`: Directory containing i18n JSON files (default: `i18n`)
- `--output PATH`: Output memory.jsonl file (default: `work/memory.jsonl`)
- `--source-lang CODE`: Source language code (default: `sv`)

### What it does

1. Reads all JSON files from the i18n directory
2. Identifies missing translations (null, empty string, empty dict)
3. Generates placeholder signatures for each translation key
4. Computes fingerprints for change detection
5. Writes memory.jsonl with deterministic ordering

## Phase 2: Validation

### Validate LLM Output

Validate a JSON file containing LLM translation output:

```bash
python -m src.cli validate response.json
```

### Write Back Translations

Merge translations from memory.jsonl into i18n files:

```bash
python -m src.cli write-back --target-lang en
```

Options:
- `--memory-file PATH`: Path to memory.jsonl (default: `work/memory.jsonl`)
- `--i18n-dir PATH`: Directory containing i18n JSON files (default: `i18n`)
- `--target-lang CODE`: Target language code (required)
- `--force`: Overwrite existing non-empty translations

## Phase 3: Translation

### Translate Missing Keys

Translate missing keys for a target language:

```bash
python -m src.cli translate-missing --target-lang en
```

Options:
- `--memory-file PATH`: Path to memory.jsonl (default: `work/memory.jsonl`)
- `--target-lang CODE`: Target language code (required)
- `--source-lang CODE`: Source language code (default: `sv`)
- `--provider PROVIDER`: Translation provider: `ollama` or `api` (default: `ollama`)
- `--model MODEL`: Ollama model name (default: `llama3.1:latest`)
- `--batch-size N`: Batch size for translations (default: `10`)
- `--runs-dir PATH`: Directory for run logs (default: `work/runs`)

## Phase 4: End-to-End Pipeline

### Run Complete Pipeline

Run the complete translation pipeline: build-memory → translate-missing → write-back

```bash
python -m src.cli run --target-lang en
```

Options:
- `--i18n-dir PATH`: Directory containing i18n JSON files (default: `i18n`)
- `--memory-file PATH`: Path to memory.jsonl (default: `work/memory.jsonl`)
- `--target-lang CODE`: Target language code (required)
- `--source-lang CODE`: Source language code (default: `sv`)
- `--provider PROVIDER`: Translation provider: `ollama` or `api` (default: `ollama`)
- `--model MODEL`: Ollama model name (default: `llama3.1:latest`)
- `--batch-size N`: Batch size for translations (default: `10`)
- `--force`: Overwrite existing non-empty translations when writing back
- `--skip-translate`: Skip translation step (useful for testing)
- `--context TEXT`: Global context for translations
- `--context-file PATH`: Path to file containing global context

### Idempotency

The pipeline is designed to be idempotent:
- **build-memory**: Always regenerates memory.jsonl from current i18n files
- **translate-missing**: Only translates keys with status "missing" (skips already-translated keys)
- **write-back**: Only updates keys where existing value is missing (unless `--force`)

Rerunning the pipeline will:
- Skip already-translated keys
- Only process newly missing translations
- Not overwrite existing translations (unless `--force`)

### Summary Reports

After translation, a summary report is displayed showing:
- Missing before/after counts
- Number of items translated
- Number of failures and validation errors
- Number of batches processed
- Repair attempts

Run logs are saved to `work/runs/<run_id>/`:
- `requests.jsonl`: All translation requests
- `responses.jsonl`: All translation responses
- `failures.jsonl`: All failures with error details
- `summary.json`: Run statistics and metadata

## Example Workflow

```bash
# 1. Build memory artifact
python -m src.cli build-memory

# 2. Translate missing keys for English
python -m src.cli translate-missing --target-lang en --model llama3.1:latest

# 3. Write back translations
python -m src.cli write-back --target-lang en

# Or run everything in one command:
python -m src.cli run --target-lang en
```

## Adding Context for Better Translations

You can provide context to improve translation accuracy:

### Global Context

Applies to all translations in a batch. Use this for general guidelines about tone, domain, or application type.

**Using command-line argument:**
```bash
python -m src.cli translate-missing --target-lang fr \
  --context "This is a mobile app. Use friendly, casual tone."
```

**Using a context file:**
```bash
python -m src.cli translate-missing --target-lang fr \
  --context-file example/context-example.txt
```

**In the run command:**
```bash
python -m src.cli run --target-lang fr \
  --context "This is a mobile booking app. Use professional, friendly tone."
```

### Per-Key Context

The system automatically extracts per-key context from the `meta` field in memory records. This allows you to provide specific context for individual translation keys.

**How to add per-key context:**

1. Edit `work/memory.jsonl` directly and add `meta` fields:
```json
{
  "key": "booking.confirm",
  "source": "Bekräfta bokning",
  "meta": {
    "description": "CTA button on checkout screen",
    "tone": "friendly",
    "screen": "Checkout",
    "domain": "E-commerce"
  }
}
```

2. Or populate meta when building memory (requires modifying build_memory function or editing JSONL after build)

**Supported meta fields:**
- `description`: Description of what the translation key represents
- `tone`: Desired tone (e.g., "friendly", "formal", "casual", "professional")
- `screen`: UI screen/context where it appears (e.g., "Checkout", "Login", "Dashboard")
- `domain`: Domain/industry context (e.g., "E-commerce", "Healthcare", "Finance")
- `notes`: Additional notes for translators

**Example with both contexts:**

When you provide both global and per-key context, the prompt will include:
- Global context at the top (applies to all)
- Per-key context inline with each item

This gives the LLM maximum context for accurate translations.

## Phase 5: Optional Hardening

- Glossary + do-not-translate support
- Stale detection when sv changes (needs_review flag)
- CI step: validate placeholders + schema without calling LLM

