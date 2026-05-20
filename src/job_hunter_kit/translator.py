from __future__ import annotations

import hashlib


def description_hash(description: str) -> str:
    normalized = " ".join(description.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def translate_text(
    text: str,
    provider: str,
    target_language: str,
    timeout_seconds: int,
) -> str:
    if not text.strip():
        return ""
    if provider != "google":
        raise ValueError("Only translation provider 'google' is currently supported.")

    try:
        from deep_translator import GoogleTranslator
    except ImportError as error:
        raise RuntimeError(
            "Translation requires deep-translator. Install dependencies with "
            '`python -m pip install -e ".[dev]"`.'
        ) from error

    return GoogleTranslator(source="auto", target=target_language).translate(text)
