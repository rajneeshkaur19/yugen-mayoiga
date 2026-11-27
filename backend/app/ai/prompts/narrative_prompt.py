"""Prompt templates and builders for Yūgen Mayoiga narrative generation.

Separates system instructions, story context serialization, player input formatting,
and output constraints into modular, clean sections.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.app.ai.language_guard import language_script_directive
from backend.app.ai.schemas import StoryAIContext

# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are the interactive narrator for Yūgen Mayoiga. Write evocative, cohesive prose that strictly honors the story's selected Genre, Tone, Theme/Premise, Season, Language, established character psychology, and player agency. Never hardcode or force a different genre than the one specified. Never invent player actions, force endings, or reference game mechanics. Weave memories and consequences naturally.

Respond ONLY with a valid JSON object:
{"narrative_text":"2-4 paragraph prose continuation","scene_title":"brief title or null","scene_mood":"mood tag or null","passage_summary":"1-2 sentence synopsis","dialogue":[{"character_name":"...","dialogue":"..."}]}
Return ONLY the JSON. No markdown, no extra text."""

# ---------------------------------------------------------------------------
# Prompt builder function
# ---------------------------------------------------------------------------


def build_narrative_user_prompt(context: StoryAIContext) -> str:
    """Format a structured StoryAIContext into a rich, comprehensive user prompt."""
    sections: list[str] = []

    # 1. Story Foundation & Theme
    runtime = context.runtime
    premise_line = ""
    if runtime.world_state and runtime.world_state.get("story_premise"):
        premise_line = f"\nPremise / Custom Concept: {runtime.world_state['story_premise']}"

    sections.append(
        "=== STORY FOUNDATION ===\n"
        f"Title: {context.story_title}\n"
        f"Genre: {context.story_genre}\n"
        f"Theme: {context.story_theme}{premise_line}\n"
        f"Tone / Mood: {context.story_tone}\n"
        f"Season: {context.story_season}\n"
        f"Target Language: {context.story_language}\n"
        f"{language_script_directive(context.story_language)}\n"
        f"Story Status: {context.story_status}"
    )

    # 2. Runtime & World State
    world_vars_str = (
        json.dumps(runtime.world_state, ensure_ascii=False)
        if runtime.world_state
        else "No external environmental changes recorded."
    )
    hidden_vars_str = (
        json.dumps(runtime.hidden_variables, ensure_ascii=False)
        if runtime.hidden_variables
        else "None"
    )
    sections.append(
        "=== RUNTIME & ATMOSPHERIC ENVIRONMENT ===\n"
        f"Turn Number: {runtime.turn_number}\n"
        f"Yūgen Meter (Mystery/Eerie Depth 0-100): {runtime.yugen_meter}\n"
        f"Atmospheric World Variables: {world_vars_str}\n"
        f"Environment Variables: {hidden_vars_str}"
    )

    # 3. Preceding and Current Scene
    if context.previous_scene:
        psc = context.previous_scene
        prev_snippet = psc.content[:200] + "..." if len(psc.content) > 200 else psc.content
        sections.append(
            "=== PRECEDING SCENE THRESHOLD ===\n"
            f"Previous Location: {psc.location} (Scene #{psc.scene_number})\n"
            f"Preceding Atmosphere: {psc.mood}\n"
            f"Preceding Environment Context: {prev_snippet}"
        )

    if context.current_scene:
        sc = context.current_scene
        haiku_line = f"\nScene Haiku: {sc.haiku}" if sc.haiku else ""
        scene_content = sc.content
        if len(scene_content) > 500:
            scene_content = scene_content[:500] + "..."
        sections.append(
            "=== CURRENT SCENE ===\n"
            f"Location: {sc.location}\n"
            f"Mood: {sc.mood}\n"
            f"Scene Number: {sc.scene_number}{haiku_line}\n"
            f"Existing Scene Description / Context:\n{scene_content}"
        )
    else:
        sections.append(
            "=== CURRENT SCENE ===\n"
            "Location: Unknown threshold / beginning\n"
            "Mood: Mysterious"
        )

    # 4. Active Characters & Psychology (capped to 3 max)
    if context.characters:
        char_blocks = []
        for ch in context.characters[:3]:
            emo = ch.emotions
            emo_str = (
                f"Fear:{emo.fear}/100, Anxiety:{emo.anxiety}/100, Anger:{emo.anger}/100, "
                f"Sadness:{emo.sadness}/100, Happiness:{emo.happiness}/100, Trust:{emo.trust}/100"
            )
            traits_str = "Standard"
            if ch.traits:
                tr = ch.traits
                traits_str = (
                    f"Openness:{tr.openness}, Conscientiousness:{tr.conscientiousness}, "
                    f"Extraversion:{tr.extraversion}, Agreeableness:{tr.agreeableness}, Neuroticism:{tr.neuroticism}"
                )
            goals_str = ", ".join(str(g) for g in ch.goals) if ch.goals else "Unknown"
            fears_str = ", ".join(str(f) for f in ch.fears) if ch.fears else "None revealed"
            secrets_str = ", ".join(str(s) for s in ch.secrets) if ch.secrets else "None known"

            char_blocks.append(
                f"- {ch.name} ({ch.role}, Age: {ch.age if ch.age is not None else 'Unknown'})\n"
                f"  Background: {ch.background}\n"
                f"  Big-Five Traits: {traits_str}\n"
                f"  Live Emotions: {emo_str}\n"
                f"  Goals: {goals_str}\n"
                f"  Fears: {fears_str}\n"
                f"  Secrets: {secrets_str}"
            )
        sections.append("=== PRESENT CHARACTERS & PSYCHOLOGICAL PROFILES ===\n" + "\n\n".join(char_blocks))
    else:
        sections.append("=== PRESENT CHARACTERS ===\nThe player travels alone.")

    # 5. Character Relationships
    if context.relationships:
        rel_lines = [
            f"- From {r.from_character_name} to {r.to_character_name}: "
            f"Trust: {r.trust}/100, Friendship: {r.friendship}/100, "
            f"Suspicion: {r.suspicion}/100, Fear: {r.fear}/100, Dependency: {r.dependency}/100"
            for r in context.relationships
        ]
        sections.append("=== INTERPERSONAL RELATIONSHIPS ===\n" + "\n".join(rel_lines))

    # 6. Retrieved Relevant Memories (capped to 2 max)
    if context.relevant_memories:
        mem_lines = []
        for m in context.relevant_memories[:2]:
            owner = f"{m.character_name}" if m.character_name else f"Character #{m.character_id}"
            mem_lines.append(
                f"- [Turn {m.created_turn} | {m.type} | Status:{m.status} | Relevance:{m.relevance_score:.2f}] "
                f"({owner}): {m.event}"
            )
        sections.append("=== RELEVANT PAST MEMORIES ===\n" + "\n".join(mem_lines))

    # 7. Recent Narrative History (capped to 2 most recent)
    if context.recent_history:
        hist_lines = []
        for h in context.recent_history[-2:]:
            action_desc = []
            if h.choice_text:
                action_desc.append(f"Chose: '{h.choice_text}'")
            if h.free_text:
                action_desc.append(f"Action: '{h.free_text}'")
            elif h.parsed_action and not h.choice_text:
                action_desc.append(f"(verb: {h.parsed_action})")
            summary = " ".join(action_desc) if action_desc else "Observed scene"
            loc_label = f" at {h.scene_location}" if h.scene_location else f" (Scene #{h.scene_id})"
            hist_lines.append(f"- Turn {h.turn_number}{loc_label}: {summary}")
        sections.append("=== RECENT PLAYER ACTION HISTORY ===\n" + "\n".join(hist_lines))

    # 8. Immediate Player Input (The catalyst for this passage)
    if context.player_input:
        pi = context.player_input
        input_details = []
        if pi.choice_text:
            input_details.append(f"Selected Decision: \"{pi.choice_text}\"")
        if pi.free_text:
            input_details.append(f"Free-form Action / Speech: \"{pi.free_text}\"")
        if pi.parsed_action:
            input_details.append(f"Parsed Action Verb: \"{pi.parsed_action}\"")
        player_action_str = "\n".join(input_details) if input_details else "The player pauses and watches silently."
    else:
        player_action_str = "The player stands still, taking in the scene and listening closely."

    sections.append(
        "=== IMMEDIATE PLAYER ACTION ===\n"
        f"{player_action_str}\n\n"
        f"DIRECTIVE: Continue the story from this exact player action while honoring Genre={context.story_genre}, "
        f"Tone={context.story_tone}, and Theme={context.story_theme}. Narrate the immediate consequences, "
        "atmospheric sensory shifts, and the responses of any characters present. Maintain psychological "
        "and physical continuity with all context above. "
        f"{language_script_directive(context.story_language)} "
        "Keep JSON keys and character names unchanged. Return ONLY the requested JSON object."
    )

    return "\n\n".join(sections)
