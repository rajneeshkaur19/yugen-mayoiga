"""Prompt templates for AI-powered consistency evaluation.

The consistency evaluator receives the original story context and the generated
narrative passage, then produces a structured JSON report identifying
contradictions, unauthorized actions, and continuity violations.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.app.ai.schemas import NarrativeGenerationResult, StoryAIContext

# ---------------------------------------------------------------------------
# System instruction for the consistency evaluator
# ---------------------------------------------------------------------------

CONSISTENCY_SYSTEM_INSTRUCTION = """You are a rigorous consistency auditor for Yūgen Mayoiga, a Japanese psychological mystery narrative game.

You receive:
1. A structured STORY CONTEXT — the ground truth of the current game state.
2. A GENERATED NARRATIVE PASSAGE — prose produced by an AI narrator.

Your role is to identify genuine, clear contradictions between the story context and the generated narrative. You are NOT a creative critic. You are a fact-checker.

EVALUATION RULES:
1. ONLY flag issues that are clearly and directly contradicted by the structured context.
2. Do NOT flag creative prose, symbolism, metaphor, dreams, hallucinations, or atmospheric embellishments as contradictions unless they explicitly contradict a stated fact.
3. Do NOT flag character growth, development, or gradual emotional shifts as contradictions. Only flag abrupt, unexplained reversals of well-established states.
4. Do NOT invent facts not present in the context. If the context is silent on a topic, do not flag it as a contradiction.
5. Be CONSERVATIVE. A false positive that blocks valid narrative is more harmful than a missed issue. When uncertain, do not raise an issue.
6. Do NOT quote or repeat large blocks of narrative text in evidence. Keep evidence concise.
7. Consider severity carefully: only use "critical" for outright ending declarations or impossible facts; "high" for clear character state inversions; "medium" for probable but arguable contradictions; "low" for minor atmospheric mismatches.

CATEGORIES TO EVALUATE:
- world_state_contradiction: Established environmental facts (fog, weather, structural damage) contradicted.
- character_behavior_contradiction: Character acts opposite to established personality, emotions, or fears without narrative justification.
- unauthorized_action: Narrative makes a decision for the player, forces an irreversible outcome, or declares an ending.
- location_continuity: Narrative introduces a new location without a supported transition.
- memory_contradiction: Narrative contradicts an established retrieved memory.
- scene_continuity: Narrative breaks established current scene details or character presence.
- factual_contradiction: Any other objectively contradicted fact from the context.
- other: Issues that do not fit other categories.

OUTPUT FORMAT — respond with ONLY a valid JSON object:
{
  "issues": [
    {
      "issue_type": "<category>",
      "severity": "<low|medium|high|critical>",
      "description": "<concise explanation of the contradiction>",
      "evidence": "<brief supporting quote from context or narrative — not longer than 2 sentences>",
      "affected_character_id": <integer or null>,
      "affected_location": "<location string or null>",
      "confidence": <integer 0-100>
    }
  ],
  "overall_confidence": <integer 0-100>,
  "summary": "<One sentence summary of findings>"
}

If no issues are found, return: {"issues": [], "overall_confidence": 95, "summary": "No consistency issues detected in the narrative passage."}
Return ONLY the JSON object. No markdown. No commentary.
"""


# ---------------------------------------------------------------------------
# User prompt builder
# ---------------------------------------------------------------------------


def build_consistency_user_prompt(
    context: StoryAIContext,
    narrative: NarrativeGenerationResult,
) -> str:
    """Build the full user prompt for the AI consistency evaluator."""
    sections: list[str] = []

    # 1. Story Foundation
    sections.append(
        "=== STORY CONTEXT (GROUND TRUTH) ===\n"
        f"Title: {context.story_title}\n"
        f"Genre: {context.story_genre}\n"
        f"Theme: {context.story_theme}\n"
        f"Tone: {context.story_tone}\n"
        f"Season: {context.story_season}"
    )

    # 2. Runtime & World State
    runtime = context.runtime
    world_vars = json.dumps(runtime.world_state, ensure_ascii=False) if runtime.world_state else "None"
    hidden_vars = json.dumps(runtime.hidden_variables, ensure_ascii=False) if runtime.hidden_variables else "None"
    sections.append(
        "=== RUNTIME STATE ===\n"
        f"Turn: {runtime.turn_number}\n"
        f"Yūgen Meter: {runtime.yugen_meter}/100\n"
        f"World State Variables: {world_vars}\n"
        f"Hidden Environment Variables: {hidden_vars}"
    )

    # 3. Current Scene
    if context.current_scene:
        sc = context.current_scene
        haiku_line = f"\nHaiku: {sc.haiku}" if sc.haiku else ""
        sections.append(
            "=== CURRENT SCENE ===\n"
            f"Location: {sc.location}\n"
            f"Mood: {sc.mood}\n"
            f"Scene Number: {sc.scene_number}\n"
            f"Is Ending Scene: {sc.is_ending}{haiku_line}\n"
            f"Scene Description: {sc.content}"
        )
    else:
        sections.append("=== CURRENT SCENE ===\nNo current scene established.")

    # 4. Characters (abbreviated — only key facts needed for checking)
    if context.characters:
        char_lines = []
        for ch in context.characters:
            emo = ch.emotions
            char_lines.append(
                f"- {ch.name} (ID:{ch.id}, Role:{ch.role})\n"
                f"  Emotions: Fear:{emo.fear}/100, Trust:{emo.trust}/100, Anxiety:{emo.anxiety}/100\n"
                f"  Fears: {', '.join(str(f) for f in ch.fears) if ch.fears else 'None stated'}\n"
                f"  Secrets (concealed): {', '.join(str(s) for s in ch.secrets) if ch.secrets else 'None'}"
            )
        sections.append("=== ESTABLISHED CHARACTERS ===\n" + "\n\n".join(char_lines))

    # 5. Relationships (trust levels matter for behavior checks)
    if context.relationships:
        rel_lines = [
            f"- {r.from_character_name} → {r.to_character_name}: "
            f"Trust:{r.trust}/100, Suspicion:{r.suspicion}/100, Fear:{r.fear}/100"
            for r in context.relationships
        ]
        sections.append("=== ESTABLISHED RELATIONSHIPS ===\n" + "\n".join(rel_lines))

    # 6. Retrieved Memories (relevant ground truth)
    if context.relevant_memories:
        mem_lines = [
            f"- [{m.type}|Turn {m.created_turn}] "
            f"({m.character_name or f'char#{m.character_id}'}): {m.event}"
            for m in context.relevant_memories
        ]
        sections.append("=== RELEVANT MEMORIES (ESTABLISHED FACTS) ===\n" + "\n".join(mem_lines))

    # 7. Recent History (what just happened)
    if context.recent_history:
        hist_lines = []
        for h in context.recent_history:
            action = h.choice_text or h.free_text or h.parsed_action or "Silent"
            hist_lines.append(f"- Turn {h.turn_number}: {action}")
        sections.append("=== RECENT PLAYER HISTORY ===\n" + "\n".join(hist_lines))

    # 8. Player's most recent action
    if context.player_input:
        pi = context.player_input
        action_parts = []
        if pi.choice_text:
            action_parts.append(f"Choice: \"{pi.choice_text}\"")
        if pi.free_text:
            action_parts.append(f"Free-text: \"{pi.free_text}\"")
        if pi.parsed_action:
            action_parts.append(f"Verb: \"{pi.parsed_action}\"")
        sections.append("=== PLAYER'S IMMEDIATE ACTION ===\n" + "\n".join(action_parts))

    # 9. The generated narrative to evaluate
    sections.append(
        "=== GENERATED NARRATIVE PASSAGE (TO EVALUATE) ===\n"
        f"{narrative.narrative_text}"
    )

    sections.append(
        "TASK: Evaluate whether the GENERATED NARRATIVE PASSAGE contradicts the STORY CONTEXT above. "
        "Return only the JSON consistency report."
    )

    return "\n\n".join(sections)
