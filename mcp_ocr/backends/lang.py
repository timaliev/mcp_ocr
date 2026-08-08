"""Shared language resolution for OCR backends.

Canonical source for language name/alias → language code mapping.
Backend-specific resolution (e.g. Vision locale arrays) stays in
the backend module; this module provides the shared alias table.
"""

_LANG_ALIASES: dict[str, str] = {
    "russian": "ru", "rus": "ru",
    "french": "fr", "fra": "fr",
    "german": "de", "ger": "de", "deu": "de",
    "spanish": "es", "spa": "es",
    "chinese": "ch", "zh": "ch", "chi": "ch", "zho": "ch",
    "english": "en", "eng": "en",
    "korean": "ko", "kor": "ko",
    "japanese": "ja", "japan": "ja", "jpn": "ja",
    "arabic": "ar", "ara": "ar",
    "italian": "it", "ita": "it",
    "portuguese": "pt", "por": "pt",
}


def resolve_lang_code(lang: str | None, default: str) -> str:
    """Resolve a language name or alias to a language code.

    Args:
        lang: Language name (e.g. "french"), alias ("fr"), or None.
        default: Fallback code when ``lang`` is None or unrecognised.

    Returns:
        Two-letter language code (e.g. "fr").
    """
    if not lang:
        return default
    return _LANG_ALIASES.get(lang.lower(), lang.lower())
