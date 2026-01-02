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
- `--provider PROVIDER`: Translation provider: `ollama`, `openai`, `openrouter`, or `claude` (default: `ollama`)
- `--model MODEL`: Ollama model name (default: `llama3.1:latest`). Ignored if `--provider` is `openai` or `openrouter`.
- `--openai-model MODEL`: OpenAI model name (default: from `OPENAI_MODEL` env or `gpt-4o-mini`). Only used if `--provider` is `openai`.
- `--openrouter-model MODEL`: OpenRouter model name (default: from `OPENROUTER_MODEL` env or `openai/gpt-4o-mini`). Only used if `--provider` is `openrouter`.
- `--claude-model MODEL`: Claude model name (default: from `ANTHROPIC_MODEL` env or `claude-3-5-sonnet-20241022`). Only used if `--provider` is `claude`.
- `--use-batch-api`: Use asynchronous batch API for Claude (50% cost savings, up to 24h processing). Only used if `--provider` is `claude`.
- `--batch-threshold N`: Auto-use batch API if items > threshold (default: 100). Only used if `--provider` is `claude`.
- `--batch-size N`: Batch size for translations (default: `10`)
- `--runs-dir PATH`: Directory for run logs (default: `work/runs`)
- `--context TEXT`: Global context for translations
- `--context-file PATH`: Path to file containing global context

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
- `--provider PROVIDER`: Translation provider: `ollama`, `openai`, `openrouter`, or `claude` (default: `ollama`)
- `--model MODEL`: Ollama model name (default: `llama3.1:latest`). Ignored if `--provider` is `openai`.
- `--openai-model MODEL`: OpenAI model name (default: from `OPENAI_MODEL` env or `gpt-4o-mini`). Only used if `--provider` is `openai`.
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

## Choosing a Translation Provider

The pipeline supports multiple LLM providers:

### Ollama (Default)

**Pros:**
- Free and runs locally
- No API costs
- Privacy: data stays on your machine
- Works offline

**Cons:**
- Requires local installation and model downloads
- Slower than cloud APIs
- Limited to models available in Ollama

**Setup:**
1. Install [Ollama](https://ollama.ai/)
2. Pull a model: `ollama pull llama3.1:latest`
3. Use with: `--provider ollama --model llama3.1:latest`

**Example:**
```bash
python -m src.cli run --target-lang fr --provider ollama --model llama3.1:latest
```

### OpenAI

**Pros:**
- Fast and reliable
- High-quality translations
- Access to latest models (GPT-4, GPT-4o-mini, etc.)
- No local setup required

**Cons:**
- Requires API key and costs money
- Data sent to external service
- Requires internet connection

**Setup:**
1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Set environment variable: `export OPENAI_API_KEY=sk-...`
3. (Optional) Set model: `export OPENAI_MODEL=gpt-4o-mini`
4. (Optional) Set custom base URL: `export OPENAI_BASE_URL=https://api.openai.com/v1`

**Example:**
```bash
export OPENAI_API_KEY=sk-your-key-here
python -m src.cli run --target-lang fr --provider openai --openai-model gpt-4o-mini
```

**Cost Considerations:**
- Pricing varies by model (GPT-4o-mini is cheaper than GPT-4)
- Costs are per token (input + output)
- Typical translation batch: ~100-500 tokens per batch
- Monitor usage at [OpenAI Usage Dashboard](https://platform.openai.com/usage)

**Troubleshooting:**
- **401 Authentication Error**: Check your API key is correct
- **403 Permission Error**: Verify your API key has access to the model
- **429 Rate Limit**: You've exceeded rate limits. The provider will retry automatically with exponential backoff
- **500/502/503 Server Error**: OpenAI service issue. The provider will retry automatically

### OpenRouter

**Pros:**
- Access to multiple LLM models through one API (OpenAI, Anthropic, Google, etc.)
- OpenAI-compatible API format
- Flexible model selection
- No local setup required

**Cons:**
- Requires API key and costs money
- Data sent to external service
- Requires internet connection
- Pricing varies by model

**Setup:**
1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set environment variable: `export OPENROUTER_API_KEY=sk-or-...`
3. (Optional) Set model: `export OPENROUTER_MODEL=openai/gpt-4o-mini`
4. (Optional) Set custom base URL: `export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
5. (Optional) Set HTTP-Referer: `export OPENROUTER_HTTP_REFERER=https://your-site.com`
6. (Optional) Set site name: `export OPENROUTER_SITE_NAME=Your App Name`

**Example:**
```bash
export OPENROUTER_API_KEY=sk-or-your-key-here
python -m src.cli run --target-lang fr --provider openrouter --openrouter-model openai/gpt-4o-mini
```

**Available Models:**
OpenRouter supports many models from different providers:
- OpenAI: `openai/gpt-4o-mini`, `openai/gpt-4o`, `openai/gpt-4-turbo`
- Anthropic: `anthropic/claude-3-5-sonnet`, `anthropic/claude-3-opus`
- Google: `google/gemini-pro`, `google/gemini-flash`
- And many more - see [OpenRouter Models](https://openrouter.ai/models)

**Cost Considerations:**
- Pricing varies by model (check [OpenRouter Pricing](https://openrouter.ai/docs/pricing))
- Costs are per token (input + output)
- Some models offer better cost/quality ratios
- Monitor usage at [OpenRouter Dashboard](https://openrouter.ai/keys)

**Troubleshooting:**
- **401 Authentication Error**: Check your API key is correct
- **403 Permission Error**: Verify your API key has access to the model
- **429 Rate Limit**: You've exceeded rate limits. The provider will retry automatically with exponential backoff
- **500/502/503 Server Error**: OpenRouter service issue. The provider will retry automatically

### Claude (Anthropic)

**Pros:**
- High-quality translations
- Access to Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- Optional batch API for 50% cost savings on large volumes
- No local setup required

**Cons:**
- Requires API key and costs money
- Data sent to external service
- Requires internet connection
- Batch API takes up to 24 hours (but 50% cheaper)

**Setup:**
1. Get an API key from [Anthropic](https://console.anthropic.com/)
2. Set environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`
3. (Optional) Set model: `export ANTHROPIC_MODEL=claude-3-5-sonnet-20241022`
4. (Optional) Set custom base URL: `export ANTHROPIC_BASE_URL=https://api.anthropic.com/v1`

**Example (Synchronous - Immediate Results):**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python -m src.cli run --target-lang fr --provider claude --claude-model claude-3-5-sonnet-20241022
```

**Example (Batch API - 50% Cost Savings, Up to 24h):**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python -m src.cli run --target-lang fr --provider claude --use-batch-api
```

**Example (Auto-detect Batch API for Large Volumes):**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python -m src.cli run --target-lang fr --provider claude --batch-threshold 100
```

**Available Models:**
- `claude-3-5-sonnet-20241022` (default, recommended)
- `claude-3-opus-20240229`
- `claude-3-haiku-20240307`

**Cost Considerations:**
- Standard API: Pay-per-token pricing
- Batch API: 50% discount on input and output tokens
- Batch API: Best for 100+ items, non-time-sensitive translations
- Monitor usage at [Anthropic Console](https://console.anthropic.com/)

**Batch API Details:**
- **When to use**: Large volumes (100+ items), cost-sensitive, can wait up to 24 hours
- **When NOT to use**: Small batches, need immediate results
- **Processing time**: Up to 24 hours (often much faster)
- **Cost savings**: 50% discount compared to standard API
- **Auto-detection**: Automatically uses batch API if items > threshold (default: 100)

**Troubleshooting:**
- **401 Authentication Error**: Check your API key is correct
- **403 Permission Error**: Verify your API key has access to the model
- **429 Rate Limit**: You've exceeded rate limits. The provider will retry automatically with exponential backoff
- **500/502/503 Server Error**: Anthropic service issue. The provider will retry automatically
- **Batch Expired/Cancelled**: Batch failed to process. Check batch status for details


## Phase 5: Optional Hardening

- Glossary + do-not-translate support
- Stale detection when sv changes (needs_review flag)
- CI step: validate placeholders + schema without calling LLM

