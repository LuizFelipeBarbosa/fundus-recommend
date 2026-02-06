import time

from deep_translator import GoogleTranslator


def translate_to_english(text: str, source_lang: str = "auto") -> str | None:
    """Translate text to English. Returns None if translation fails or text is already English."""
    if not text or not text.strip():
        return None

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = GoogleTranslator(source=source_lang, target="en").translate(text)
            return result if result and result.strip() else None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                return None


def translate_batch(texts: list[str], source_lang: str = "auto", delay: float = 0.1) -> list[str | None]:
    """Translate a batch of texts with rate limiting."""
    results: list[str | None] = []
    for text in texts:
        results.append(translate_to_english(text, source_lang))
        time.sleep(delay)
    return results
