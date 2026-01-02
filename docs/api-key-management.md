# API Key Management Patterns

This document outlines common patterns for managing API keys in Python applications, with recommendations for this project.

## Current Pattern (Environment Variables)

The project currently uses **environment variables** for API key management, which is the most common and secure approach for command-line tools.

### Implementation
```python
import os

api_key = api_key or os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key required. Set OPENAI_API_KEY environment variable.")
```

### Usage
```bash
export OPENAI_API_KEY=sk-your-key-here
python -m src.cli run --target-lang en --provider openai
```

## Common API Key Management Options

### 1. Environment Variables (✅ Currently Used)

**Pros:**
- ✅ Secure (not stored in code or files)
- ✅ Works well with CI/CD systems
- ✅ Standard practice for command-line tools
- ✅ Easy to use with shell scripts
- ✅ No additional dependencies

**Cons:**
- ❌ Must be set in each shell session
- ❌ Can be forgotten/not set

**Best for:** Production use, CI/CD, scripts, command-line tools

**Implementation:**
```python
import os
api_key = os.getenv("API_KEY_NAME")
```

---

### 2. `.env` Files with `python-dotenv`

**Pros:**
- ✅ Keys stored in one place (`.env` file)
- ✅ Easy to manage multiple keys
- ✅ Can be gitignored (security)
- ✅ Works well for development

**Cons:**
- ❌ Requires `python-dotenv` dependency
- ❌ `.env` file can be accidentally committed
- ❌ Must remember to create `.env` file

**Best for:** Development, projects with multiple API keys

**Implementation:**
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env file
api_key = os.getenv("API_KEY_NAME")
```

**Example `.env` file:**
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

---

### 3. Config Files (JSON/YAML/TOML)

**Pros:**
- ✅ Structured configuration
- ✅ Can store multiple settings
- ✅ Human-readable

**Cons:**
- ❌ Security risk if committed to git
- ❌ Must manage file location
- ❌ More complex to implement

**Best for:** Complex applications with many settings

**Implementation:**
```python
import json
from pathlib import Path

config_path = Path.home() / ".config" / "app" / "config.json"
with open(config_path) as f:
    config = json.load(f)
api_key = config["api_keys"]["openai"]
```

---

### 4. Command-Line Arguments

**Pros:**
- ✅ Explicit and visible
- ✅ Good for one-off scripts

**Cons:**
- ❌ Security risk (visible in process list, shell history)
- ❌ Inconvenient for repeated use
- ❌ Can leak in logs

**Best for:** One-off scripts, testing (not recommended for production)

**Implementation:**
```python
import argparse
parser.add_argument("--api-key", help="API key")
```

---

### 5. Interactive Prompts

**Pros:**
- ✅ User-friendly
- ✅ No keys stored anywhere

**Cons:**
- ❌ Not suitable for automation/CI
- ❌ Must enter each time
- ❌ Can't use in scripts

**Best for:** Interactive tools, one-time setup

**Implementation:**
```python
import getpass
api_key = getpass.getpass("Enter API key: ")
```

---

### 6. Keychain/Credential Stores

**Pros:**
- ✅ Secure (OS-level encryption)
- ✅ Persistent across sessions
- ✅ No files to manage

**Cons:**
- ❌ Platform-specific
- ❌ Requires additional libraries
- ❌ More complex implementation

**Best for:** Desktop applications, user-facing tools

**Libraries:**
- `keyring` (cross-platform)
- macOS: `keychain`
- Windows: `wincred`

**Implementation:**
```python
import keyring
api_key = keyring.get_password("app_name", "api_key")
```

---

## Recommendation for This Project

### Primary: Environment Variables (Current Pattern) ✅

**Why:**
- Already implemented and working
- Standard practice for CLI tools
- Secure and CI/CD friendly
- No additional dependencies
- Works well with shell scripts and automation

**Usage:**
```bash
# Set once per session
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-...

# Or in shell profile (~/.bashrc, ~/.zshrc)
echo 'export OPENAI_API_KEY=sk-...' >> ~/.zshrc
```

### Optional Enhancement: `.env` File Support

**If users request it**, we could add optional `.env` file support using `python-dotenv`:

```python
# Optional: Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads .env from current directory
except ImportError:
    pass  # python-dotenv not installed, skip

# Then fall back to environment variables
api_key = os.getenv("API_KEY_NAME")
```

**Benefits:**
- Users can create `.env` file for convenience
- Still falls back to environment variables
- Optional dependency (graceful degradation)

**Trade-off:**
- Adds optional dependency
- Must document `.env` file format
- Users must remember to add `.env` to `.gitignore`

---

## Security Best Practices

1. **Never commit API keys to git**
   - Add `.env` to `.gitignore` if using `.env` files
   - Use environment variables in CI/CD

2. **Use different keys for different environments**
   - Development key
   - Production key
   - Test key

3. **Rotate keys regularly**
   - Especially if exposed or compromised

4. **Use least-privilege keys**
   - Only grant necessary permissions
   - Use read-only keys when possible

5. **Document key requirements clearly**
   - In README
   - In error messages
   - In setup instructions

---

## Example: Multi-Provider Setup

With environment variables (recommended):

```bash
# ~/.zshrc or ~/.bashrc
export OPENAI_API_KEY=sk-proj-...
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-...

# Usage
python -m src.cli run --target-lang fr --provider openai
python -m src.cli run --target-lang fr --provider claude
python -m src.cli run --target-lang fr --provider openrouter
```

With `.env` file (if we add support):

```bash
# .env (in project root, gitignored)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Usage (same as above)
python -m src.cli run --target-lang fr --provider openai
```

---

## Summary

**Current approach (environment variables) is recommended** because:
- ✅ Secure
- ✅ Standard practice
- ✅ CI/CD friendly
- ✅ No dependencies
- ✅ Already implemented

**Optional enhancement:** Add `.env` file support for user convenience, but keep it optional and maintain environment variable fallback.

