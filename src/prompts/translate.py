"""Prompt builder for translation requests."""

from typing import List, Dict, Optional


def build_translation_prompt(
    source_lang: str,
    target_lang: str,
    items: List[Dict[str, str]],
    global_context: Optional[str] = None,
    per_key_context: Optional[Dict[str, Dict[str, str]]] = None
) -> str:
    """
    Build a translation prompt for the LLM.
    
    Args:
        source_lang: Source language code (e.g., "sv")
        target_lang: Target language code (e.g., "de")
        items: List of items to translate, each with "key" and "text"
        global_context: Optional global context string (e.g., "This is a mobile app for booking hotels. Use formal tone.")
        per_key_context: Optional dict mapping keys to context dicts (e.g., {"booking.confirm": {"description": "CTA button", "tone": "friendly"}})
    
    Returns:
        Prompt string for the LLM
    """
    lang_names = {
        "sv": "Swedish",
        "en": "English",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
    }
    
    source_name = lang_names.get(source_lang, source_lang)
    target_name = lang_names.get(target_lang, target_lang)
    
    # Build items list
    # Escape backslashes in text for display in prompt (so \1 shows as \1, not control char)
    def escape_for_prompt(text: str) -> str:
        """Escape backslashes for display in prompt string."""
        return text.replace('\\', '\\\\')
    
    # Build items list with optional per-key context
    items_lines = []
    for item in items:
        key = item["key"]
        text = escape_for_prompt(item["text"])
        line = f'- {key}: "{text}"'
        
        # Add per-key context if available
        if per_key_context and key in per_key_context:
            context = per_key_context[key]
            context_parts = []
            if "description" in context:
                context_parts.append(f"Description: {context['description']}")
            if "tone" in context:
                context_parts.append(f"Tone: {context['tone']}")
            if "screen" in context:
                context_parts.append(f"Screen: {context['screen']}")
            if "domain" in context:
                context_parts.append(f"Domain: {context['domain']}")
            if "notes" in context:
                context_parts.append(f"Notes: {context['notes']}")
            
            if context_parts:
                line += f" ({'; '.join(context_parts)})"
        
        items_lines.append(line)
    
    items_text = "\n".join(items_lines)
    
    # Build context section
    context_section = ""
    if global_context:
        context_section = f"\nCONTEXT:\n{global_context}\n"
    
    prompt = f"""You are a translation API. Return ONLY valid JSON. No markdown, no commentary, no explanation.

Translate these {source_name} strings to {target_name}:{context_section}
{items_text}

RULES:
- Return ONLY the JSON object below. Nothing else.
- Preserve protected tokens EXACTLY: {{name}} stays {{name}}, \\1 stays \\\\1 in JSON
- Translate only the text around protected tokens
- Escape backslashes in JSON: \\1 becomes \\\\1
- Follow the context and tone guidelines provided above

Return this exact JSON structure (replace with your translations):
{{
  "targetLanguage": "{target_lang}",
  "translations": [
    {{"key": "error.404", "text": "Erreur \\\\1: Page non trouvée"}}
  ]
}}
"""
    return prompt


def build_json_schema_prompt() -> str:
    """
    Build a JSON schema description for the LLM.
    
    Returns:
        JSON schema description string
    """
    return """The response must be valid JSON matching this schema:
{
  "targetLanguage": "string (language code)",
  "translations": [
    {
      "key": "string (translation key)",
      "text": "string (translated text)"
    }
  ]
}"""

