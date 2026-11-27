"""Language fidelity guard for AI-generated narrative and choice outputs.

Ensures that when a non-English language (especially non-Latin scripts such as
Japanese or Hindi) is requested, the model's output actually contains text in
that language rather than silently returning English.
"""

from __future__ import annotations

import re
from typing import Tuple

_JAPANESE_SCRIPT_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")
_DEVANAGARI_SCRIPT_RE = re.compile(r"[\u0900-\u097f]")
_FRENCH_MARKERS_RE = re.compile(
    r"[àâäæçéèêëîïôœùûüÿ]|"
    r"\b(le|la|les|un|une|des|et|ou|dans|sur|avec|pour|est|sont|vous|nous|je|tu|il|elle|"
    r"ce|cette|qui|que|quoi|mais|où|pas|plus|aux|du|au|mon|ton|son|ma|ta|sa)\b",
    re.IGNORECASE,
)


def validate_output_language(text: str, story_language: str) -> Tuple[bool, str | None]:
    """Check whether ``text`` plausibly matches ``story_language``.

    Returns ``(True, None)`` when valid, or ``(False, reason)`` when the output
    clearly fails to match the requested language.
    """
    lang = (story_language or "English").strip()
    clean = (text or "").strip()
    if not clean:
        return False, f"Empty output received for requested language '{lang}'."

    if lang == "Japanese":
        if not _JAPANESE_SCRIPT_RE.search(clean):
            return (
                False,
                "Model output did not contain Japanese script (Hiragana/Katakana/Kanji) "
                "even though Japanese was requested.",
            )
        return True, None

    if lang == "Hindi":
        if not _DEVANAGARI_SCRIPT_RE.search(clean):
            return (
                False,
                "Model output did not contain Devanagari script "
                "even though Hindi was requested.",
            )
        return True, None

    if lang == "French":
        # Allow short strings if they have at least one French marker; for longer passages
        # require at least one French diacritic or common French function word.
        if len(clean) >= 25 and not _FRENCH_MARKERS_RE.search(clean):
            return (
                False,
                "Model output did not appear to be in French even though French was requested.",
            )
        return True, None

    return True, None


def language_script_directive(story_language: str) -> str:
    """Return an explicit, unambiguous language & script directive for prompts."""
    lang = (story_language or "English").strip()
    if lang == "Japanese":
        return (
            "CRITICAL LANGUAGE REQUIREMENT: Write ALL player-facing prose, titles, moods, "
            "summaries, dialogue, and choice text in natural Japanese (日本語 — Kanji, Hiragana, "
            "and Katakana). Do NOT write English prose."
        )
    if lang == "Hindi":
        return (
            "CRITICAL LANGUAGE REQUIREMENT: Write ALL player-facing prose, titles, moods, "
            "summaries, dialogue, and choice text in natural Hindi using Devanagari script "
            "(हिन्दी — देवनागरी लिपि). Do NOT write English or Romanized Hindi."
        )
    if lang == "French":
        return (
            "CRITICAL LANGUAGE REQUIREMENT: Write ALL player-facing prose, titles, moods, "
            "summaries, dialogue, and choice text in natural French (Français). "
            "Do NOT write English prose."
        )
    return (
        "LANGUAGE REQUIREMENT: Write ALL player-facing prose, titles, moods, "
        "summaries, dialogue, and choice text in natural English."
    )
