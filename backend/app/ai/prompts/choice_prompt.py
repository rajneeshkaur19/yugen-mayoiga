"""Prompt templates and builders for dynamic AI choice generation in Yūgen Mayoiga.

Generates contextual, atmospheric, and actionable choices that respect
player agency and deterministic world state without producing generic filler.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.app.ai.language_guard import language_script_directive
from backend.app.ai.schemas import StoryAIContext

CHOICE_SYSTEM_INSTRUCTION = """You are the choice designer for Yūgen Mayoiga. Generate 2-4 vivid, context-specific choices grounded in the current scene, previous decisions, and the story's selected Genre, Tone, Theme, and Language. No generic filler ("Look around", "Wait"). Each choice must be sensory, evocative, and unique. Never duplicate existing choices.

Output ONLY valid JSON with this exact structure — no markdown, no explanation:
{"choices":[{"choice_id":"dynamic_ai_1","choice_text":"<under 120 chars>","action_intent":"inspect","target":"<string or null>","approach":"<string or null>","risk_level":"low"}]}

Fields: choice_id (string), choice_text (<120 chars), action_intent (inspect/speak/search/use/move/take/wait), target (string|null), approach (string|null), risk_level (low|medium|high).
"""


def build_choice_user_prompt(
    context: StoryAIContext,
    existing_choices: Optional[list[str]] = None,
    max_choices: int = 3,
) -> str:
    """Format a StoryAIContext and existing choices into a detailed prompt for dynamic choice generation."""
    sections: list[str] = []

    # 1. Story & Scene Foundation
    sections.append(f"### STORY ID {context.story_id}: \"{context.story_title}\"")
    sections.append(
        f"Genre: {context.story_genre} | Tone: {context.story_tone} | Theme: {context.story_theme} | "
        f"Season: {context.story_season} | Language: {context.story_language}"
    )
    sections.append(language_script_directive(context.story_language))

    if context.current_scene:
        sc = context.current_scene
        sections.append(f"\n### CURRENT SCENE (ID: {sc.id}, #{sc.scene_number})")
        sections.append(f"Location: {sc.location}")
        sections.append(f"Mood: {sc.mood}")
        sections.append(f"Is Ending Scene: {sc.is_ending}")
        sections.append(f"Scene Prose:\n{sc.content}")
        if sc.haiku:
            sections.append(f"Haiku Motif: {sc.haiku}")
    else:
        sections.append("\n### CURRENT SCENE: Unknown or prologue")

    # 2. Characters & Psychological State
    if context.characters:
        sections.append("\n### PRESENT CHARACTERS & PSYCHOLOGICAL STATES")
        for char in context.characters:
            emo = char.emotions
            emo_str = (
                f"Fear={emo.fear}, Anxiety={emo.anxiety}, Anger={emo.anger}, "
                f"Sadness={emo.sadness}, Happiness={emo.happiness}, Trust={emo.trust}"
            )
            char_line = f"- {char.name} ({char.role}): {emo_str}."
            if char.fears:
                char_line += f" Fears: {', '.join(str(f) for f in char.fears[:2])}."
            sections.append(char_line)

    # 3. Directed Relationships
    if context.relationships:
        sections.append("\n### ACTIVE RELATIONSHIPS")
        for rel in context.relationships:
            sections.append(
                f"- {rel.from_character_name} -> {rel.to_character_name}: "
                f"Trust={rel.trust}, Friendship={rel.friendship}, Suspicion={rel.suspicion}"
            )

    # 4. World State & Environment Flags
    if context.runtime and context.runtime.world_state:
        sections.append("\n### WORLD STATE FLAGS")
        for k, v in sorted(context.runtime.world_state.items()):
            sections.append(f"- {k}: {v}")

    # 5. Relevant Memories
    if context.relevant_memories:
        sections.append("\n### RECALLED MEMORIES / CLUES")
        for m in context.relevant_memories:
            sections.append(f"- {m.event}")

    # 6. Recent History
    if context.recent_history:
        sections.append("\n### RECENT LOGGED ACTIONS")
        for h in context.recent_history[-3:]:
            action = h.choice_text or h.free_text or h.parsed_action or "Unspecified action"
            sections.append(f"- Turn {h.turn_number}: {action}")

    # 7. Existing Deterministic Choices (to avoid duplication)
    if existing_choices:
        sections.append("\n### EXISTING PREDEFINED CHOICES (DO NOT DUPLICATE THESE)")
        for ec in existing_choices:
            sections.append(f"- \"{ec}\"")

    # 8. Output reminder for Phi-3 compatibility
    sections.append(
        "\nIMPORTANT: Respond with ONLY a JSON object. No text before or after.\n"
        'Example: {"choices":[{"choice_id":"dynamic_ai_1","choice_text":"...","action_intent":"inspect","target":"...","approach":null,"risk_level":"low"}]}'
    )

    # 9. Request & constraints
    sections.append(f"\n### GENERATION TASK")
    sections.append(
        f"Generate {max_choices} distinct, evocative, context-grounded choices for the player in this moment, "
        f"matching Genre={context.story_genre} and Tone={context.story_tone}. "
        "Each choice must explore a different angle or intent and reflect recent player decisions. "
        f"{language_script_directive(context.story_language)} "
        "Keep JSON keys, action_intent enums, IDs, and schema unchanged. Return strictly valid JSON."
    )

    return "\n".join(sections)
