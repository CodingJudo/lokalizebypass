# i18n LLM Translator

A simple pipeline that translates missing i18n strings using LLM providers. Only translates missing keys, preserves existing translations and placeholders.

## Installation

**Prerequisites:**
- Python 3.11+
- (Optional) [Ollama](https://ollama.ai/) for local translation (free)

**Install:**
```bash
pip install -e .
```

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Quick Start

### 1. Prepare your translation files

Create a folder with your JSON files (e.g., `i18n/`):

```json
// i18n/en.json (source language)
{
  "welcome": "Welcome, {{name}}!",
  "button.save": "Save",
  "error.not_found": "Page not found"
}
```

```json
// i18n/fr.json (target language - missing translations)
{
  "welcome": null,
  "button.save": null,
  "error.not_found": null
}
```

### 2. Translate missing keys

**Using Ollama (local, free):**
```bash
# Start Ollama and pull a model first
ollama pull llama3.1:latest

# Translate missing French keys
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr
```

**Using OpenAI (cloud, requires API key):**
```bash
export OPENAI_API_KEY=sk-your-key-here
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr --provider openai
```

**Using Claude (cloud, requires API key):**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr --provider claude
```

**Using OpenRouter (cloud, requires API key):**
```bash
export OPENROUTER_API_KEY=sk-or-your-key-here
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr --provider openrouter
```

### 3. Check results

Your `i18n/fr.json` will now have translations filled in:

```json
{
  "welcome": "Bienvenue, {{name}} !",
  "button.save": "Enregistrer",
  "error.not_found": "Page non trouvée"
}
```

## Features

- ✅ **Safe**: Never overwrites existing translations
- ✅ **Smart**: Preserves placeholders like `{{name}}`, `{count}`, `%s`
- ✅ **Resumable**: Can rerun safely - only translates missing keys
- ✅ **Multiple providers**: Ollama (local), OpenAI, Claude, OpenRouter

## Examples

**Translate multiple languages:**
```bash
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang de
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang es
```

**Add context for better translations:**
```bash
# Create context file
echo "This is a mobile booking app. Use friendly, professional tone." > context.txt

# Use context during translation
python -m src.cli run --i18n-dir i18n --source-lang en --target-lang fr \
  --context-file context.txt
```

**Use specific files instead of directory:**
```bash
python -m src.cli run \
  --source-file i18n/en.json \
  --target-file i18n/fr.json \
  --source-lang en \
  --target-lang fr
```

## Translation Providers

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| **Ollama** | Local | Free | Install [Ollama](https://ollama.ai/) |
| **OpenAI** | Cloud | Paid | Set `OPENAI_API_KEY` env var |
| **Claude** | Cloud | Paid | Set `ANTHROPIC_API_KEY` env var |
| **OpenRouter** | Cloud | Paid | Set `OPENROUTER_API_KEY` env var |

See [docs/runbook.md](docs/runbook.md) for detailed provider comparison and usage.

## Development

```bash
# Run tests
pytest

# Install in development mode
pip install -e .
```

