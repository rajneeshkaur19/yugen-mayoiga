"""AI Consistency Checker for Yūgen Mayoiga (AI Phase 3).

Evaluates a generated narrative passage against the structured StoryAIContext
and returns a detailed :class:`ConsistencyReport`.

Architecture — two layers:

**Layer 1 — Deterministic checks**
    Fast, rule-based validation derived purely from structured data.
    Conservative: only flags clear, grounded contradictions.

**Layer 2 — AI semantic evaluation**
    Uses the existing LLM provider to reason about subtle inconsistencies
    that cannot be caught by simple keyword/value rules.
    Optional: if the provider is unavailable, deterministic results are
    preserved and the report notes which categories were unchecked.

Guarantees:
- Strictly read-only. No database access. No state mutations.
- Never mutates the narrative passage.
- Never automatically retries narrative generation.
- Never raises unhandled exceptions into the caller — always returns a report.
- If AI validation is unavailable, the report explicitly marks affected
  categories as unavailable instead of claiming full verification.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from pydantic import ValidationError

from backend.app.ai.exceptions import (
    AIConfigurationError,
    AINarrativeError,
    AIProviderError,
    AIResponseValidationError,
)
from backend.app.ai.prompts.consistency_prompt import (
    CONSISTENCY_SYSTEM_INSTRUCTION,
    build_consistency_user_prompt,
)
from backend.app.ai.providers import BaseLLMProvider, get_default_provider
from backend.app.ai.schemas import (
    CheckStatus,
    ConsistencyIssue,
    ConsistencyReport,
    IssueCategory,
    IssueSeverity,
    NarrativeGenerationResult,
    StoryAIContext,
)

# ---------------------------------------------------------------------------
# Severity ordering for sorting and threshold logic
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {
    IssueSeverity.CRITICAL: 4,
    IssueSeverity.HIGH: 3,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.LOW: 1,
}

# Categories evaluated by the AI semantic layer
_AI_CATEGORIES = [
    IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION,
    IssueCategory.UNAUTHORIZED_ACTION,
    IssueCategory.LOCATION_CONTINUITY,
    IssueCategory.MEMORY_CONTRADICTION,
    IssueCategory.SCENE_CONTINUITY,
    IssueCategory.FACTUAL_CONTRADICTION,
]

# Categories evaluated by deterministic layer
_DETERMINISTIC_CATEGORIES = [
    IssueCategory.WORLD_STATE_CONTRADICTION,
    IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION,
    IssueCategory.SCENE_CONTINUITY,
]


def _narrative_lower(narrative: NarrativeGenerationResult) -> str:
    """Return full narrative text lowercased for keyword scanning."""
    return narrative.narrative_text.lower()


# ---------------------------------------------------------------------------
# Layer 1 — Deterministic Checks
# ---------------------------------------------------------------------------


def _check_world_state(
    context: StoryAIContext,
    narrative: NarrativeGenerationResult,
) -> list[ConsistencyIssue]:
    """Check world-state variables against narrative text conservatively."""
    issues: list[ConsistencyIssue] = []
    text_lower = _narrative_lower(narrative)
    world = context.runtime.world_state
    hidden = context.runtime.hidden_variables

    # Merge both dicts — only check boolean/string "flag" values
    all_vars = {**world, **hidden}

    # Fog contradiction
    fog_level = str(all_vars.get("fog_level", "")).lower() or str(all_vars.get("fog", "")).lower()
    if fog_level in ("heavy", "oppressive", "dense", "thick"):
        # Only flag very explicit sunny/clear descriptions
        clear_markers = ["clear sky", "bright sunshine", "blazing sun", "cloudless", "sunny day"]
        for marker in clear_markers:
            if marker in text_lower:
                issues.append(
                    ConsistencyIssue(
                        issue_type=IssueCategory.WORLD_STATE_CONTRADICTION,
                        severity=IssueSeverity.MEDIUM,
                        description=(
                            f"World state establishes '{fog_level}' fog, but narrative "
                            f"describes '{marker}' without an explained transition."
                        ),
                        evidence=f"World variable fog_level='{fog_level}'; narrative contains '{marker}'.",
                        confidence=70,
                    )
                )
                break

    # Scene mood contradiction (only flag direct antonyms)
    if context.current_scene:
        scene_mood = context.current_scene.mood.lower()
        mood_antonyms = {
            "foreboding": ["cheerful", "joyful", "festive", "merry", "serene peace"],
            "terror": ["peaceful", "pleasant", "comfortable"],
            "eerie": ["bright and sunny", "warm and welcoming"],
        }
        for mood_key, antonyms in mood_antonyms.items():
            if mood_key in scene_mood:
                for antonym in antonyms:
                    if antonym in text_lower:
                        issues.append(
                            ConsistencyIssue(
                                issue_type=IssueCategory.WORLD_STATE_CONTRADICTION,
                                severity=IssueSeverity.LOW,
                                description=(
                                    f"Scene mood is '{context.current_scene.mood}', "
                                    f"but narrative atmosphere describes '{antonym}'."
                                ),
                                evidence=f"Scene mood: '{context.current_scene.mood}'; narrative: '{antonym}'.",
                                confidence=50,
                            )
                        )
                        break

    return issues


def _check_scene_continuity(
    context: StoryAIContext,
    narrative: NarrativeGenerationResult,
) -> list[ConsistencyIssue]:
    """Check whether the narrative erroneously declares an ending or resets the scene."""
    issues: list[ConsistencyIssue] = []
    text_lower = _narrative_lower(narrative)

    if context.current_scene and not context.current_scene.is_ending:
        # Only flag very explicit ending declarations without engine authorization
        ending_phrases = [
            "the story ends",
            "your journey is over",
            "the game is over",
            "you have reached the end",
            "credits roll",
        ]
        for phrase in ending_phrases:
            if phrase in text_lower:
                issues.append(
                    ConsistencyIssue(
                        issue_type=IssueCategory.SCENE_CONTINUITY,
                        severity=IssueSeverity.CRITICAL,
                        description=(
                            "Narrative declares a story ending, but the current scene "
                            "is not marked as an ending scene by the game engine."
                        ),
                        evidence=f"Narrative contains '{phrase}'; current scene is_ending=False.",
                        confidence=90,
                    )
                )
                break

    return issues


def _check_character_trust_extremes(
    context: StoryAIContext,
    narrative: NarrativeGenerationResult,
) -> list[ConsistencyIssue]:
    """Flag abrupt trust reversals for characters with extreme distrust (≤15)."""
    issues: list[ConsistencyIssue] = []
    text_lower = _narrative_lower(narrative)

    for char in context.characters:
        if char.emotions.trust <= 15:
            # Only flag very explicit unconditional trust/love declarations
            unconditional_phrases = [
                f"{char.name.lower()} trusts you completely",
                f"{char.name.lower()} loves you",
                f"{char.name.lower()} fully trusts",
                f"{char.name.lower()} embraces you warmly",
            ]
            for phrase in unconditional_phrases:
                if phrase in text_lower:
                    issues.append(
                        ConsistencyIssue(
                            issue_type=IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION,
                            severity=IssueSeverity.HIGH,
                            description=(
                                f"{char.name} has trust={char.emotions.trust}/100 (extreme distrust), "
                                f"but narrative asserts unconditional trust without transition."
                            ),
                            evidence=f"Character trust={char.emotions.trust}/100; narrative contains '{phrase}'.",
                            affected_character_id=char.id,
                            confidence=80,
                        )
                    )
                    break

    return issues


def run_deterministic_checks(
    context: StoryAIContext,
    narrative: NarrativeGenerationResult,
) -> tuple[list[ConsistencyIssue], list[IssueCategory]]:
    """Run all deterministic checks and return (issues, checked_categories)."""
    all_issues: list[ConsistencyIssue] = []
    checked: set[IssueCategory] = set()

    world_issues = _check_world_state(context, narrative)
    all_issues.extend(world_issues)
    checked.add(IssueCategory.WORLD_STATE_CONTRADICTION)

    scene_issues = _check_scene_continuity(context, narrative)
    all_issues.extend(scene_issues)
    checked.add(IssueCategory.SCENE_CONTINUITY)

    if context.characters:
        char_issues = _check_character_trust_extremes(context, narrative)
        all_issues.extend(char_issues)
        checked.add(IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION)

    return all_issues, list(checked)


# ---------------------------------------------------------------------------
# Layer 2 — AI Semantic Evaluation helpers
# ---------------------------------------------------------------------------


def _strip_fence(text: str) -> str:
    """Strip markdown code fences from AI output."""
    clean = text.strip()
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", clean, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return clean


def _parse_ai_issues(
    raw_text: str,
) -> tuple[list[ConsistencyIssue], int, str, bool]:
    """Parse and validate AI evaluator JSON response.

    Returns (issues, overall_confidence, summary, success).
    """
    clean = _strip_fence(raw_text)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        return [], 0, "AI evaluator returned malformed JSON.", False

    if not isinstance(data, dict):
        return [], 0, "AI evaluator returned unexpected data type.", False

    raw_issues = data.get("issues", [])
    overall_confidence = data.get("overall_confidence", 50)
    summary = data.get("summary", "AI evaluation completed.")

    if not isinstance(overall_confidence, int):
        try:
            overall_confidence = int(overall_confidence)
        except (TypeError, ValueError):
            overall_confidence = 50
    overall_confidence = max(0, min(100, overall_confidence))

    parsed_issues: list[ConsistencyIssue] = []
    if isinstance(raw_issues, list):
        for raw in raw_issues:
            if not isinstance(raw, dict):
                continue
            # Remap confidence
            conf = raw.get("confidence", 50)
            try:
                conf = int(conf)
            except (TypeError, ValueError):
                conf = 50
            conf = max(0, min(100, conf))

            try:
                issue = ConsistencyIssue(
                    issue_type=raw.get("issue_type", IssueCategory.OTHER),
                    severity=raw.get("severity", IssueSeverity.LOW),
                    description=raw.get("description", "Unspecified issue."),
                    evidence=raw.get("evidence", "No evidence provided."),
                    affected_character_id=raw.get("affected_character_id"),
                    affected_location=raw.get("affected_location"),
                    confidence=conf,
                )
                parsed_issues.append(issue)
            except (ValidationError, Exception):
                # Skip malformed individual issue entries
                continue

    return parsed_issues, overall_confidence, summary, True


# ---------------------------------------------------------------------------
# Public ConsistencyChecker class
# ---------------------------------------------------------------------------


class ConsistencyChecker:
    """Evaluates narrative consistency against structured story context.

    Uses two layers:
    - Layer 1: Fast deterministic rule-based checks.
    - Layer 2: AI semantic evaluation (requires a configured provider).

    Returns a :class:`ConsistencyReport` in all cases — never raises
    into the caller even if the AI layer fails.
    """

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        skip_ai_check: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        provider:
            Pre-configured LLM provider. If None, resolved lazily from env.
        skip_ai_check:
            If True, only deterministic checks are run (useful for testing
            or when AI is not configured).
        """
        self._provider = provider
        self.skip_ai_check = skip_ai_check

    @property
    def provider(self) -> Optional[BaseLLMProvider]:
        """Return the provider, or None if configuration is missing."""
        if self.skip_ai_check:
            return None
        if self._provider is not None:
            return self._provider
        try:
            self._provider = get_default_provider()
            return self._provider
        except AIConfigurationError:
            return None

    def check(
        self,
        context: StoryAIContext,
        narrative: NarrativeGenerationResult,
    ) -> ConsistencyReport:
        """Run the full consistency check and return a :class:`ConsistencyReport`.

        Never raises into the caller. All failures are captured in the report.

        Parameters
        ----------
        context:
            The StoryAIContext assembled by StoryContextBuilder (Phase 1).
        narrative:
            The NarrativeGenerationResult from NarrativeGenerator (Phase 2).

        Returns
        -------
        ConsistencyReport
            Fully populated report regardless of provider availability.
        """
        # Validate inputs
        if not isinstance(context, StoryAIContext):
            return self._make_error_report(
                "Invalid context type passed to ConsistencyChecker.",
                checked=[],
                unavailable=list(IssueCategory),
            )
        if not isinstance(narrative, NarrativeGenerationResult):
            return self._make_error_report(
                "Invalid narrative type passed to ConsistencyChecker.",
                checked=[],
                unavailable=list(IssueCategory),
            )

        # ── Layer 1: Deterministic checks ────────────────────────────────────
        deterministic_issues, deterministic_checked = run_deterministic_checks(context, narrative)

        # ── Layer 2: AI semantic evaluation ──────────────────────────────────
        ai_issues: list[ConsistencyIssue] = []
        ai_checked: list[IssueCategory] = []
        ai_unavailable: list[IssueCategory] = []
        ai_confidence: Optional[int] = None
        ai_summary: Optional[str] = None
        ai_provider = self.provider

        if ai_provider is None:
            # Provider not configured — mark all AI categories as unavailable
            ai_unavailable = [c for c in _AI_CATEGORIES if c not in deterministic_checked]
        else:
            try:
                prompt = build_consistency_user_prompt(context, narrative)
                raw_text, _ = ai_provider.generate(
                    prompt=prompt,
                    system_instruction=CONSISTENCY_SYSTEM_INSTRUCTION,
                )
                ai_issues_parsed, ai_confidence, ai_summary, success = _parse_ai_issues(raw_text)
                if success:
                    ai_issues = ai_issues_parsed
                    ai_checked = [c for c in _AI_CATEGORIES if c not in deterministic_checked]
                else:
                    ai_unavailable = [c for c in _AI_CATEGORIES if c not in deterministic_checked]
            except (AIProviderError, AINarrativeError, Exception):
                # Catch all provider failures — preserve deterministic results
                ai_unavailable = [c for c in _AI_CATEGORIES if c not in deterministic_checked]

        # ── Assemble final report ─────────────────────────────────────────────
        all_issues = deterministic_issues + ai_issues

        # Sort by severity descending
        all_issues.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 0), reverse=True)

        # Determine is_consistent: no medium/high/critical issues
        significant_severities = {IssueSeverity.MEDIUM, IssueSeverity.HIGH, IssueSeverity.CRITICAL}
        is_consistent = not any(i.severity in significant_severities for i in all_issues)

        # Checked and unavailable categories (deduplicated)
        all_checked = list(dict.fromkeys(deterministic_checked + ai_checked))
        all_unavailable = [c for c in ai_unavailable if c not in all_checked]

        # Overall confidence
        if ai_confidence is not None:
            # Average deterministic confidence (~90) with AI confidence
            overall_confidence = (90 + ai_confidence) // 2
        elif ai_unavailable:
            # AI unavailable — lower confidence
            overall_confidence = 60
        else:
            overall_confidence = 85

        # Determine status
        if all_unavailable:
            if all_issues:
                status = CheckStatus.ISSUES_FOUND
            else:
                status = CheckStatus.PARTIAL
        elif all_issues:
            status = CheckStatus.ISSUES_FOUND
        else:
            status = CheckStatus.PASSED

        # Summary
        if ai_summary:
            summary = ai_summary
        elif all_issues:
            critical_count = sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL)
            high_count = sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH)
            summary = (
                f"Found {len(all_issues)} consistency issue(s): "
                f"{critical_count} critical, {high_count} high severity."
            )
        elif all_unavailable:
            summary = (
                f"Deterministic checks passed; {len(all_unavailable)} "
                "category/categories could not be AI-evaluated."
            )
        else:
            summary = "No consistency issues detected in the narrative passage."

        return ConsistencyReport(
            is_consistent=is_consistent,
            issues=all_issues,
            overall_confidence=overall_confidence,
            check_status=status,
            checked_categories=all_checked,
            unavailable_categories=all_unavailable,
            summary=summary,
        )

    @staticmethod
    def _make_error_report(
        reason: str,
        checked: list[IssueCategory],
        unavailable: list[IssueCategory],
    ) -> ConsistencyReport:
        """Return a minimal report describing a checker configuration error."""
        return ConsistencyReport(
            is_consistent=False,
            issues=[
                ConsistencyIssue(
                    issue_type=IssueCategory.OTHER,
                    severity=IssueSeverity.HIGH,
                    description=reason,
                    evidence="Internal checker error — no narrative evaluation was performed.",
                    confidence=100,
                )
            ],
            overall_confidence=0,
            check_status=CheckStatus.UNAVAILABLE,
            checked_categories=checked,
            unavailable_categories=unavailable,
            summary=f"Consistency check failed: {reason}",
        )
