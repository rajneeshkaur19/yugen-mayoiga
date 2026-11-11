"""Emotion Engine for Yūgen Mayoiga.

Handles:
- Emotion deltas for Big Six emotions (fear, anxiety, anger, sadness, happiness, trust)
- Clamping strictly between 0 and 100
- Emotion decay toward baseline per scene/turn
- Memory reinforcement from important memories
- Persistence in character_states table
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithms.state_store import (
    DEFAULT_EMOTION_BASELINES,
    EMOTIONS,
    clamp,
)
from backend.app.models.character import Character
from backend.app.models.character_state import CharacterState
from backend.app.models.memory import Memory


def get_latest_character_state(
    db: Session,
    story_id: int,
    character_id: int,
) -> CharacterState | None:
    """Retrieve the most recent emotion snapshot for a character in a story."""
    return db.scalar(
        select(CharacterState)
        .where(
            CharacterState.story_id == story_id,
            CharacterState.character_id == character_id,
        )
        .order_by(CharacterState.turn_number.desc())
    )


def get_character_emotions_dict(
    db: Session,
    story_id: int,
    character_id: int,
) -> dict[str, int]:
    """Return latest emotion values as a dictionary, falling back to baselines."""
    latest = get_latest_character_state(db, story_id, character_id)
    if latest is None:
        return {e: DEFAULT_EMOTION_BASELINES.get(e, 50) for e in EMOTIONS}
    return {
        "fear": latest.fear,
        "anxiety": latest.anxiety,
        "anger": latest.anger,
        "sadness": latest.sadness,
        "happiness": latest.happiness,
        "trust": latest.trust,
    }


def calculate_decayed_emotions(
    current_emotions: dict[str, int],
    decay_rate: int = 5,
    baselines: dict[str, int] | None = None,
) -> dict[str, int]:
    """Calculate decayed emotion values toward baselines."""
    target_baselines = baselines or DEFAULT_EMOTION_BASELINES
    result: dict[str, int] = {}
    for emo in EMOTIONS:
        base = target_baselines.get(emo, DEFAULT_EMOTION_BASELINES.get(emo, 50))
        val = current_emotions.get(emo, base)
        if val > base:
            result[emo] = max(base, val - decay_rate)
        elif val < base:
            result[emo] = min(base, val + decay_rate)
        else:
            result[emo] = val
    return result


def apply_memory_reinforcement(
    db: Session,
    story_id: int,
    character_id: int,
    emotions: dict[str, int],
    threshold_importance: int = 70,
    damping: float = 0.15,
) -> dict[str, int]:
    """Reinforce emotions based on recent high-importance memories."""
    recent_memories = list(
        db.scalars(
            select(Memory)
            .where(
                Memory.story_id == story_id,
                Memory.character_id == character_id,
                Memory.importance >= threshold_importance,
            )
            .order_by(Memory.created_turn.desc())
            .limit(3)
        ).all()
    )

    reinforced = dict(emotions)
    for mem in recent_memories:
        weight = mem.emotional_weight
        imp = mem.importance
        delta = int(round((imp / 100.0) * weight * damping))

        # Positive emotional weight strengthens happiness and trust; negative strengthens fear and anxiety
        if weight > 0:
            reinforced["happiness"] = clamp(reinforced["happiness"] + delta)
            reinforced["trust"] = clamp(reinforced["trust"] + delta // 2)
        elif weight < 0:
            abs_delta = abs(delta)
            reinforced["fear"] = clamp(reinforced["fear"] + abs_delta)
            reinforced["anxiety"] = clamp(reinforced["anxiety"] + abs_delta)
            reinforced["trust"] = clamp(reinforced["trust"] - abs_delta // 2)

    return reinforced


def record_character_emotions(
    db: Session,
    story_id: int,
    character_id: int,
    scene_id: int,
    turn_number: int,
    deltas: dict[str, int] | None = None,
    decay: bool = True,
    decay_rate: int = 5,
    reinforce: bool = True,
) -> CharacterState:
    """Compute and persist an emotion snapshot for a character at a specific turn.

    Step 1: Fetch previous emotion values (or baselines).
    Step 2: Optionally apply decay.
    Step 3: Apply choice/event deltas.
    Step 4: Optionally reinforce from important memories.
    Step 5: Insert or update CharacterState row in PostgreSQL.
    """
    character_exists = db.scalar(
        select(Character.id).where(
            Character.id == character_id,
            Character.story_id == story_id,
        )
    )
    if character_exists is None:
        raise ValueError(
            f"Character {character_id} does not belong to story {story_id}."
        )

    current = get_character_emotions_dict(db, story_id, character_id)

    if decay:
        current = calculate_decayed_emotions(current, decay_rate=decay_rate)

    if deltas:
        for emo, d in deltas.items():
            if emo in EMOTIONS and isinstance(d, (int, float)):
                current[emo] = clamp(current[emo] + int(d))

    if reinforce:
        current = apply_memory_reinforcement(db, story_id, character_id, current)

    # Check if a snapshot already exists for (character_id, turn_number)
    state = db.scalar(
        select(CharacterState).where(
            CharacterState.story_id == story_id,
            CharacterState.character_id == character_id,
            CharacterState.turn_number == turn_number,
        )
    )

    if state is None:
        state = CharacterState(
            story_id=story_id,
            character_id=character_id,
            scene_id=scene_id,
            turn_number=turn_number,
            fear=current["fear"],
            anxiety=current["anxiety"],
            anger=current["anger"],
            sadness=current["sadness"],
            happiness=current["happiness"],
            trust=current["trust"],
        )
        db.add(state)
    else:
        state.scene_id = scene_id
        state.fear = current["fear"]
        state.anxiety = current["anxiety"]
        state.anger = current["anger"]
        state.sadness = current["sadness"]
        state.happiness = current["happiness"]
        state.trust = current["trust"]

    return state
