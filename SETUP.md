# Setup and Usage Guide

## Initial Setup on a New Computer

### 1. Prerequisites

**Install Python 3.11+**
```bash
# Check Python version
python3 --version  # Should be 3.11 or higher

# If needed, install Python 3.11+ from python.org or using a package manager
```

**Install Ollama (for local LLM translation)**
```bash
# macOS
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull llama3.1:latest
```

### 2. Install the Application

```bash
# Clone or download the repository
cd lokalizebypass

# Install the application
pip install -e .

# Or install dependencies manually
pip install requests
```

### 3. Verify Installation

```bash
# Check that commands work
python -m src.cli --help
python -m src.cli build-memory --help
```

## Running on Your Files

### Step 1: Prepare Your Files

Create a folder with your translation files. For example, if you have 3 files:

```
my-translations/
  en.json    # Source language (English)
  fr.json    # Target language 1 (French)
  de.json    # Target language 2 (German)
```

**Example `en.json` (source):**
```json
{
  "welcome": "Welcome, {{username}}!",
  "booking.confirm": "Confirm booking",
  "error.404": "Error \\1: Page not found"
}
```

**Example `fr.json` (target - can be empty or have some translations):**
```json
{
  "welcome": null,
  "booking.confirm": null,
  "error.404": null
}
```

### Step 2: Create Context File (Optional but Recommended)

Create a file with context about your application:

```bash
# Create context file
cat > my-translations/context.txt << 'EOF'
This is a mobile booking application for hotels.
Use a friendly, professional tone suitable for customer-facing interactions.
Keep translations concise and clear.
Domain: Travel and hospitality
EOF
```

### Step 3: Build Memory Artifact

```bash
# Build memory from your files
python -m src.cli build-memory \
  --i18n-dir my-translations \
  --source-lang en \
  --output work/my-memory.jsonl
```

This creates `work/my-memory.jsonl` with all translation keys and their status.

### Step 4: Translate Missing Keys

**For French (fr):**
```bash
python -m src.cli translate-missing \
  --memory-file work/my-memory.jsonl \
  --target-lang fr \
  --source-lang en \
  --context-file my-translations/context.txt \
  --model llama3.1:latest
```

**For German (de):**
```bash
python -m src.cli translate-missing \
  --memory-file work/my-memory.jsonl \
  --target-lang de \
  --source-lang en \
  --context-file my-translations/context.txt \
  --model llama3.1:latest
```

### Step 5: Write Back Translations

**For French:**
```bash
python -m src.cli write-back \
  --memory-file work/my-memory.jsonl \
  --i18n-dir my-translations \
  --target-lang fr
```

**For German:**
```bash
python -m src.cli write-back \
  --memory-file work/my-memory.jsonl \
  --i18n-dir my-translations \
  --target-lang de
```

### Alternative: Run Everything in One Command

```bash
# For French
python -m src.cli run \
  --i18n-dir my-translations \
  --target-lang fr \
  --source-lang en \
  --context-file my-translations/context.txt \
  --model llama3.1:latest

# For German (run separately)
python -m src.cli run \
  --i18n-dir my-translations \
  --target-lang de \
  --source-lang en \
  --context-file my-translations/context.txt \
  --model llama3.1:latest
```

## Complete Example Workflow

```bash
# 1. Setup (one time)
pip install -e .
ollama pull llama3.1:latest

# 2. Prepare your files in my-translations/ folder
#    - en.json (source)
#    - fr.json (target 1)
#    - de.json (target 2)
#    - context.txt (optional context)

# 3. Run for French
python -m src.cli run \
  --i18n-dir my-translations \
  --target-lang fr \
  --source-lang en \
  --context-file my-translations/context.txt

# 4. Run for German
python -m src.cli run \
  --i18n-dir my-translations \
  --target-lang de \
  --source-lang en \
  --context-file my-translations/context.txt

# 5. Check results
cat my-translations/fr.json
cat my-translations/de.json
```

## What Each Step Does

1. **build-memory**: Scans all JSON files, identifies missing translations, generates placeholder signatures
2. **translate-missing**: Uses LLM to translate missing keys, validates results
3. **write-back**: Merges translations back into your JSON files (only updates missing values)

## Tips

- **Context matters**: The context file helps the LLM understand tone, domain, and style
- **Protected tokens**: Tokens like `{{username}}` and `\1` are automatically preserved
- **Idempotent**: Safe to rerun - won't overwrite existing translations
- **Check logs**: Run logs are in `work/runs/<run_id>/` for debugging

