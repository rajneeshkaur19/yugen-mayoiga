"""Integrated rule-driven narrative action pipeline for YÅ«gen Mayoiga.

Executes atomic state updates for a player choice or action in a single database transaction:
1. Verify story ownership & fetch current state
2. Validate choice selection & condition check
3. Read configured choice effects
4. Apply character emotion deltas & decay across scene transition
5. Apply directed relationship changes
6. Apply world-state modifications
7. Update hidden variables & YÅ«gen Meter
8. Create player-choice and emotional memories
9. Promote and trigger scheduled events (using PriorityEventManager logic)
10. Evaluate conditional endings
11. Advance current_scene_id and turn_number
12. Append to user_choices_log
13. Commit atomically; rollback on any failure
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithms.priority_events import PriorityEventManager, StoryEvent
from algorithms.state_store import EMOTIONS, clamp
from backend.app.models.character import Character
from backend.app.models.choice import Choice
from backend.app.models.event import Event
from backend.app.models.memory import Memory
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.services.emotion_engine import record_character_emotions
from backend.app.services.ending_engine import (
    check_and_trigger_endings,
    evaluate_condition_clause,
)
from backend.app.services.relationship_engine import apply_relationship_deltas
from backend.app.services.state_service import (
    get_or_create_story_state,
    get_unified_story_state,
    update_hidden_variables,
    update_yugen_meter,
)
from backend.app.services.world_state_engine import update_world_state


def process_story_action(
    db: Session,
    user_id: int,
    story_id: int,
    choice_id: int | None = None,
    free_text: str | None = None,
    active_character_id: int | None = None,
) -> dict[str, Any]:
    """Execute the integrated state update pipeline atomically inside one transaction."""

    try:
        # 1. Verify story ownership
        story = db.scalar(
            select(Story).where(
                Story.id == story_id,
                Story.user_id == user_id,
            )
        )
        if story is None:
            raise ValueError(f"Story {story_id} not found or does not belong to user {user_id}.")

        # 2. Get current state and scene
        story_state = get_or_create_story_state(db, story_id, commit=False)
        current_scene_id = story_state.current_scene_id
        next_turn = story_state.turn_number + 1

        current_scene = db.scalar(
            select(Scene).where(
                Scene.id == current_scene_id,
                Scene.story_id == story_id,
            )
        )
        if current_scene is None:
            raise ValueError(f"Current scene {current_scene_id} not found in story {story_id}.")

        # 3. Validate choice if provided
        choice: Choice | None = None
        if choice_id is not None:
            choice = db.scalar(
                select(Choice).where(
                    Choice.id == choice_id,
                    Choice.scene_id == current_scene_id,
                    Choice.story_id == story_id,
                )
            )
            if choice is None:
                raise ValueError(
                    f"Choice {choice_id} is not an available option for current scene {current_scene_id}."
                )

        if choice is None and not free_text:
            raise ValueError("Either a choice_id or free_text action must be supplied.")

        # 4. Extract effects
        raw_effects: dict[str, Any] = choice.effects if choice else {}
        action_text: str = choice.choice_text if choice else (free_text or "")

        # 5. Determine active character (default to first character in story if unspecified)
        if active_character_id is None:
            first_char = db.scalar(
                select(Character.id).where(Character.story_id == story_id)
            )
            active_character_id = first_char

        # 6. Apply Emotion Updates & Decay
        emotion_deltas: dict[str, int] = {}
        if "emotions" in raw_effects and isinstance(raw_effects["emotions"], dict):
            for k, v in raw_effects["emotions"].items():
                if isinstance(v, dict):
                    record_character_emotions(
                        db,
                        story_id=story_id,
                        character_id=int(k),
                        scene_id=choice.next_scene_id if (choice and choice.next_scene_id) else current_scene_id,
                        turn_number=next_turn,
                        deltas=v,
                        decay=True,
                    )
                elif k in EMOTIONS and active_character_id is not None:
                    emotion_deltas[k] = int(v)

        # Flat emotion deltas
        for emo in EMOTIONS:
            if emo in raw_effects and isinstance(raw_effects[emo], (int, float)):
                emotion_deltas[emo] = int(raw_effects[emo])

        if active_character_id is not None:
            record_character_emotions(
                db,
                story_id=story_id,
                character_id=active_character_id,
                scene_id=choice.next_scene_id if (choice and choice.next_scene_id) else current_scene_id,
                turn_number=next_turn,
                deltas=emotion_deltas,
                decay=True,
            )

        # 7. Apply Relationship Changes
        if "relationships" in raw_effects and isinstance(raw_effects["relationships"], dict):
            for rel_key, rel_deltas in raw_effects["relationships"].items():
                if isinstance(rel_key, (list, tuple)) and len(rel_key) == 2:
                    fc, tc = int(rel_key[0]), int(rel_key[1])
                    apply_relationship_deltas(db, story_id, fc, tc, rel_deltas)
                elif isinstance(rel_key, str) and "->" in rel_key:
                    parts = rel_key.split("->")
                    fc, tc = int(parts[0].strip()), int(parts[1].strip())
                    apply_relationship_deltas(db, story_id, fc, tc, rel_deltas)

        # 8. Apply World State Modifications
        world_updates = raw_effects.get("world", {})
        if not isinstance(world_updates, dict):
            world_updates = {}
        for k, v in raw_effects.items():
            if k.startswith("world_"):
                world_updates[k[6:]] = v
        if world_updates:
            update_world_state(db, story_id, world_updates)

        # 9. Update Hidden Variables & YÅ«gen Meter
        hidden_updates = raw_effects.get("hidden", {})
        if not isinstance(hidden_updates, dict):
            hidden_updates = {}
        for k, v in raw_effects.items():
            if k.startswith("hidden_"):
                hidden_updates[k[7:]] = v
        if hidden_updates:
            update_hidden_variables(db, story_id, hidden_updates)

        # YÅ«gen meter adjustment
        yugen_delta = int(raw_effects.get("yugen_meter", 0))
        if yugen_delta:
            update_yugen_meter(db, story_id, yugen_delta)

        # 10. Create Memory
        if active_character_id is not None:
            memory_event = f"Selected: '{action_text}' in {current_scene.location}"
            mem_record = Memory(
                story_id=story_id,
                character_id=active_character_id,
                event=memory_event,
                type="player_choice",
                importance=int(raw_effects.get("memory_importance", 50)),
                emotional_weight=int(raw_effects.get("emotional_weight", 0)),
                status="normal",
                created_turn=next_turn,
            )
            db.add(mem_record)

        # 11. Process scheduled events through the priority queue.
        due_events = list(
            db.scalars(
                select(Event)
                .where(
                    Event.story_id == story_id,
                    Event.status.in_(("pending", "ready")),
                    Event.due_turn <= next_turn,
                )
                .order_by(Event.due_turn.asc(), Event.id.asc())
            ).all()
        )

        event_manager = PriorityEventManager()
        for ev in due_events:
            event_manager.add_event(
                StoryEvent(
                    event_id=str(ev.id),
                    due_time=ev.due_turn,
                    priority=ev.priority,
                    payload=ev,
                )
            )

        event_manager.schedule_pending()
        event_manager.promote_due_events(next_turn)

        triggered_events_desc: list[str] = []
        event_scene_id = (
            choice.next_scene_id
            if choice is not None and choice.next_scene_id is not None
            else current_scene_id
        )

        while True:
            queued_event = event_manager.pop_ready_event()
            if queued_event is None:
                break

            ev = queued_event.payload
            conditions = ev.trigger_condition or {}

            if not isinstance(conditions, dict):
                raise ValueError(
                    f"Event {ev.id} trigger_condition must be a JSON object."
                )

            current_event_state = get_unified_story_state(
                db, story_id, include_hidden=True
            )
            conditions_met = all(
                evaluate_condition_clause(key, rule, current_event_state)
                for key, rule in conditions.items()
            )

            if not conditions_met:
                ev.status = "ready"
                continue

            event_effects = ev.effects or {}
            if not isinstance(event_effects, dict):
                raise ValueError(f"Event {ev.id} effects must be a JSON object.")

            # Apply emotion deltas.
            event_emotions = event_effects.get("emotions", {})
            if not isinstance(event_emotions, dict):
                event_emotions = {}

            event_flat_emotions: dict[str, int] = {}

            for character_key, deltas in event_emotions.items():
                if isinstance(deltas, dict):
                    record_character_emotions(
                        db,
                        story_id=story_id,
                        character_id=int(character_key),
                        scene_id=event_scene_id,
                        turn_number=next_turn,
                        deltas=deltas,
                        decay=True,
                    )
                elif character_key in EMOTIONS and active_character_id is not None:
                    event_flat_emotions[character_key] = int(deltas)

            for emotion in EMOTIONS:
                if isinstance(event_effects.get(emotion), (int, float)):
                    event_flat_emotions[emotion] = int(event_effects[emotion])

            if active_character_id is not None and event_flat_emotions:
                record_character_emotions(
                    db,
                    story_id=story_id,
                    character_id=active_character_id,
                    scene_id=event_scene_id,
                    turn_number=next_turn,
                    deltas=event_flat_emotions,
                    decay=True,
                )

            # Apply directed relationship deltas.
            event_relationships = event_effects.get("relationships", {})
            if isinstance(event_relationships, dict):
                for rel_key, rel_deltas in event_relationships.items():
                    if isinstance(rel_key, (list, tuple)) and len(rel_key) == 2:
                        from_char, to_char = int(rel_key[0]), int(rel_key[1])
                    elif isinstance(rel_key, str) and "->" in rel_key:
                        parts = rel_key.split("->")
                        if len(parts) != 2:
                            raise ValueError(
                                f"Invalid relationship key in event {ev.id}: {rel_key}"
                            )
                        from_char, to_char = int(parts[0].strip()), int(parts[1].strip())
                    else:
                        raise ValueError(
                            f"Invalid relationship key in event {ev.id}: {rel_key}"
                        )

                    apply_relationship_deltas(
                        db, story_id, from_char, to_char, rel_deltas
                    )

            # Apply world-state updates.
            event_world = event_effects.get("world", {})
            if not isinstance(event_world, dict):
                raise ValueError(f"Event {ev.id} world effects must be an object.")

            for key, value in event_effects.items():
                if key.startswith("world_"):
                    event_world[key[6:]] = value

            if event_world:
                update_world_state(db, story_id, event_world)

            # Apply hidden-variable updates.
            event_hidden = event_effects.get("hidden", {})
            if not isinstance(event_hidden, dict):
                raise ValueError(f"Event {ev.id} hidden effects must be an object.")

            for key, value in event_effects.items():
                if key.startswith("hidden_"):
                    event_hidden[key[7:]] = value

            if event_hidden:
                update_hidden_variables(db, story_id, event_hidden)

            # Apply Yugen meter delta.
            event_yugen_delta = int(event_effects.get("yugen_meter", 0))
            if event_yugen_delta:
                update_yugen_meter(db, story_id, event_yugen_delta)

            ev.status = "done"
            triggered_events_desc.append(ev.description)

        # 12. Advance scene destination
        destination_scene_id = current_scene_id
        if choice and choice.next_scene_id:
            destination_scene_id = choice.next_scene_id

        dest_scene = db.scalar(
            select(Scene).where(
                Scene.id == destination_scene_id,
                Scene.story_id == story_id,
            )
        )

        story_state.current_scene_id = destination_scene_id
        story_state.turn_number = next_turn

        # 13. Evaluate Endings against updated unified state
        unified_state = get_unified_story_state(db, story_id, include_hidden=True)
        achieved_endings = check_and_trigger_endings(
            db, story_id=story_id, user_id=user_id, current_state=unified_state
        )

        # 14. Append to user_choices_log
        log_entry = UserChoicesLog(
            user_id=user_id,
            story_id=story_id,
            turn_number=next_turn,
            scene_id=current_scene_id,
            choice_id=choice_id,
            free_text=free_text,
            parsed_action=action_text[:100],
            delta=raw_effects,
            undone=False,
        )
        db.add(log_entry)

        # Commit single atomic transaction
        db.commit()
        db.refresh(story_state)

        # Build clean user response
        return {
            "story_id": story_id,
            "turn_number": story_state.turn_number,
            "current_scene_id": story_state.current_scene_id,
            "scene_content": dest_scene.content if dest_scene else "",
            "scene_location": dest_scene.location if dest_scene else "",
            "scene_mood": dest_scene.mood if dest_scene else "",
            "is_ending": bool(dest_scene.is_ending) if dest_scene else False,
            "yugen_meter": story_state.yugen_meter,
            "applied_effects": raw_effects,
            "triggered_events": triggered_events_desc,
            "achieved_endings": [
                {"id": e.id, "name": e.name, "seal_text": e.seal_text}
                for e in achieved_endings
            ],
        }

    except Exception:
        db.rollback()
        raise
