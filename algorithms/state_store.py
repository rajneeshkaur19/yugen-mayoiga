"""Hash-map based state store with clamping and effect application for Yūgen Mayoiga.

Provides O(1) average-time operations for:
- Character emotion updates with 0-100 clamping
- Emotion decay toward baseline
- Emotion reinforcement from memories
- Relationship updates with directionality and clamping
- Key-value world state management
- Hidden variables and Yūgen Meter calculations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def clamp(value: float | int, min_val: float | int = 0, max_val: float | int = 100) -> int:
    """Clamp a numeric value between min_val and max_val (inclusive), rounded to integer."""
    return int(max(min_val, min(max_val, round(value))))


# Supported Big Six emotions
EMOTIONS = ("fear", "anxiety", "anger", "sadness", "happiness", "trust")

# Supported relationship attributes
RELATIONSHIP_ATTRS = ("trust", "friendship", "suspicion", "fear", "dependency")

# Baseline values for emotions (default is 50 for neutral, or 0 for acute negative states)
DEFAULT_EMOTION_BASELINES: dict[str, int] = {
    "fear": 0,
    "anxiety": 0,
    "anger": 0,
    "sadness": 0,
    "happiness": 50,
    "trust": 50,
}


@dataclass
class StateStore:
    """In-memory state container providing fast O(1) operations and rule validation."""

    # character_id -> {emotion_name: int (0-100)}
    emotions: dict[int, dict[str, int]] = field(default_factory=dict)

    # (from_char_id, to_char_id) -> {attr_name: int (0-100)}
    relationships: dict[tuple[int, int], dict[str, int]] = field(default_factory=dict)

    # key -> value (JSON-serializable)
    world_state: dict[str, Any] = field(default_factory=dict)

    # key -> value
    hidden_variables: dict[str, Any] = field(default_factory=dict)

    # 0-100 metric representing unresolved mystery
    yugen_meter: int = 50

    # -------------------------------------------------------------------------
    # Emotion Operations
    # -------------------------------------------------------------------------

    def init_character_emotions(
        self,
        character_id: int,
        initial: dict[str, int] | None = None,
    ) -> dict[str, int]:
        """Initialise emotion map for a character."""
        base = {e: DEFAULT_EMOTION_BASELINES.get(e, 50) for e in EMOTIONS}
        if initial:
            for k, v in initial.items():
                if k in EMOTIONS:
                    base[k] = clamp(v)
        self.emotions[character_id] = base
        return self.emotions[character_id]

    def get_emotions(self, character_id: int) -> dict[str, int]:
        """Return emotions for a character, initialising defaults if not present."""
        if character_id not in self.emotions:
            return self.init_character_emotions(character_id)
        return self.emotions[character_id]

    def apply_emotion_delta(
        self,
        character_id: int,
        emotion: str,
        delta: int,
    ) -> int:
        """Apply delta to a specific emotion and return clamped new value."""
        if emotion not in EMOTIONS:
            raise ValueError(f"Unknown emotion '{emotion}'. Supported: {EMOTIONS}")
        curr = self.get_emotions(character_id)
        new_val = clamp(curr[emotion] + delta)
        curr[emotion] = new_val
        return new_val

    def apply_emotion_deltas(
        self,
        character_id: int,
        deltas: dict[str, int],
    ) -> dict[str, int]:
        """Apply multiple emotion deltas to a character."""
        for emo, d in deltas.items():
            if emo in EMOTIONS:
                self.apply_emotion_delta(character_id, emo, d)
        return self.get_emotions(character_id)

    def decay_emotions(
        self,
        character_id: int,
        decay_rate: int = 5,
        baselines: dict[str, int] | None = None,
    ) -> dict[str, int]:
        """Decay emotions toward their baseline values by at most decay_rate points."""
        curr = self.get_emotions(character_id)
        target_baselines = baselines or DEFAULT_EMOTION_BASELINES
        for emo in EMOTIONS:
            target = target_baselines.get(emo, DEFAULT_EMOTION_BASELINES.get(emo, 50))
            current_val = curr.get(emo, target)
            if current_val > target:
                curr[emo] = max(target, current_val - decay_rate)
            elif current_val < target:
                curr[emo] = min(target, current_val + decay_rate)
        return curr

    def reinforce_emotion(
        self,
        character_id: int,
        emotion: str,
        importance: int,
        emotional_weight: int,
        damping: float = 0.2,
    ) -> int:
        """Reinforce or sustain an emotion based on memory importance and weight.

        Formula: delta = round((importance / 100.0) * emotional_weight * damping)
        """
        if emotion not in EMOTIONS:
            raise ValueError(f"Unknown emotion '{emotion}'")
        delta = int(round((clamp(importance) / 100.0) * emotional_weight * damping))
        return self.apply_emotion_delta(character_id, emotion, delta)

    # -------------------------------------------------------------------------
    # Relationship Operations
    # -------------------------------------------------------------------------

    def init_relationship(
        self,
        from_char: int,
        to_char: int,
        initial: dict[str, int] | None = None,
    ) -> dict[str, int]:
        """Initialise directed relationship from from_char to to_char."""
        if from_char == to_char:
            raise ValueError("Relationships cannot be self-referential")
        base = {
            "trust": 50,
            "friendship": 50,
            "suspicion": 0,
            "fear": 0,
            "dependency": 0,
        }
        if initial:
            for k, v in initial.items():
                if k in RELATIONSHIP_ATTRS:
                    base[k] = clamp(v)
        self.relationships[(from_char, to_char)] = base
        return base

    def get_relationship(self, from_char: int, to_char: int) -> dict[str, int]:
        """Get directed relationship, initialising defaults if absent."""
        if from_char == to_char:
            raise ValueError("Relationships cannot be self-referential")
        key = (from_char, to_char)
        if key not in self.relationships:
            return self.init_relationship(from_char, to_char)
        return self.relationships[key]

    def apply_relationship_delta(
        self,
        from_char: int,
        to_char: int,
        attribute: str,
        delta: int,
    ) -> int:
        """Apply delta to an attribute of a directed relationship."""
        if attribute not in RELATIONSHIP_ATTRS:
            raise ValueError(
                f"Unknown relationship attribute '{attribute}'. Supported: {RELATIONSHIP_ATTRS}"
            )
        rel = self.get_relationship(from_char, to_char)
        new_val = clamp(rel[attribute] + delta)
        rel[attribute] = new_val
        return new_val

    def apply_relationship_deltas(
        self,
        from_char: int,
        to_char: int,
        deltas: dict[str, int],
    ) -> dict[str, int]:
        """Apply multiple deltas to a directed relationship."""
        for attr, d in deltas.items():
            if attr in RELATIONSHIP_ATTRS:
                self.apply_relationship_delta(from_char, to_char, attr, d)
        return self.get_relationship(from_char, to_char)

    # -------------------------------------------------------------------------
    # World State Operations
    # -------------------------------------------------------------------------

    def set_world_var(self, key: str, value: Any) -> None:
        """Set a world state variable."""
        self.world_state[key] = value

    def get_world_var(self, key: str, default: Any = None) -> Any:
        """Get a world state variable."""
        return self.world_state.get(key, default)

    def update_world_state(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update multiple world state variables."""
        self.world_state.update(updates)
        return self.world_state

    # -------------------------------------------------------------------------
    # Hidden Variables and Yūgen Meter
    # -------------------------------------------------------------------------

    def set_hidden_var(self, key: str, value: Any) -> None:
        """Set a hidden narrative variable."""
        self.hidden_variables[key] = value

    def get_hidden_var(self, key: str, default: Any = None) -> Any:
        """Get a hidden variable."""
        return self.hidden_variables.get(key, default)

    def update_hidden_vars(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update multiple hidden variables."""
        for k, v in updates.items():
            # If value is numeric and existing is numeric, check if delta or replacement
            # Standard convention: if ends with "_delta", treat as addition
            if k.endswith("_delta") and isinstance(v, (int, float)):
                actual_k = k[:-6]
                curr = self.hidden_variables.get(actual_k, 0)
                if isinstance(curr, (int, float)):
                    self.hidden_variables[actual_k] = curr + v
                else:
                    self.hidden_variables[actual_k] = v
            else:
                self.hidden_variables[k] = v
        return self.hidden_variables

    def update_yugen_meter(self, delta: int) -> int:
        """Update the Yūgen Meter by delta, clamping to 0-100."""
        self.yugen_meter = clamp(self.yugen_meter + delta)
        return self.yugen_meter

    # -------------------------------------------------------------------------
    # Unified Choice Effect Processing
    # -------------------------------------------------------------------------

    def apply_choice_effects(
        self,
        effects: dict[str, Any],
        active_character_id: int | None = None,
    ) -> dict[str, Any]:
        """Apply arbitrary structured or flat choice effects deterministically.

        Supports nested structures:
        - effects["emotions"]: {char_id: {emotion: delta}} or {emotion: delta}
        - effects["relationships"]: {(from, to): {attr: delta}} or {attr: delta}
        - effects["world"]: {key: value}
        - effects["hidden"]: {key: value}
        - effects["yugen_meter"]: int delta

        Or flat effects:
        - effects["trust"]: delta
        - effects["fear"]: delta
        - effects["power"]: "off"
        """
        applied: dict[str, Any] = {
            "emotions": {},
            "relationships": {},
            "world": {},
            "hidden": {},
            "yugen_meter_delta": 0,
        }

        # 1. Nested emotions
        if "emotions" in effects and isinstance(effects["emotions"], dict):
            for k, v in effects["emotions"].items():
                if isinstance(v, dict):
                    # k is character_id
                    try:
                        cid = int(k)
                        self.apply_emotion_deltas(cid, v)
                        applied["emotions"][cid] = v
                    except ValueError:
                        pass
                elif k in EMOTIONS and active_character_id is not None:
                    # k is emotion name, v is delta
                    self.apply_emotion_delta(active_character_id, k, int(v))
                    applied["emotions"].setdefault(active_character_id, {})[k] = int(v)

        # 2. Nested relationships
        if "relationships" in effects and isinstance(effects["relationships"], dict):
            for k, v in effects["relationships"].items():
                if isinstance(k, (tuple, list)) and len(k) == 2 and isinstance(v, dict):
                    fc, tc = int(k[0]), int(k[1])
                    self.apply_relationship_deltas(fc, tc, v)
                    applied["relationships"][(fc, tc)] = v
                elif isinstance(k, str) and "->" in k and isinstance(v, dict):
                    parts = k.split("->")
                    fc, tc = int(parts[0].strip()), int(parts[1].strip())
                    self.apply_relationship_deltas(fc, tc, v)
                    applied["relationships"][(fc, tc)] = v

        # 3. Nested world variables
        if "world" in effects and isinstance(effects["world"], dict):
            self.update_world_state(effects["world"])
            applied["world"].update(effects["world"])

        # 4. Nested hidden variables
        if "hidden" in effects and isinstance(effects["hidden"], dict):
            self.update_hidden_vars(effects["hidden"])
            applied["hidden"].update(effects["hidden"])

        # 5. Yūgen meter
        if "yugen_meter" in effects:
            ym_delta = int(effects["yugen_meter"])
            self.update_yugen_meter(ym_delta)
            applied["yugen_meter_delta"] = ym_delta

        # 6. Flat format support
        for k, v in effects.items():
            if k in ("emotions", "relationships", "world", "hidden", "yugen_meter"):
                continue
            if k in EMOTIONS and active_character_id is not None and isinstance(v, (int, float)):
                self.apply_emotion_delta(active_character_id, k, int(v))
                applied["emotions"].setdefault(active_character_id, {})[k] = int(v)
            elif k in RELATIONSHIP_ATTRS and active_character_id is not None:
                # If target specified in hidden or default
                pass
            elif k.startswith("world_"):
                var_name = k[6:]
                self.set_world_var(var_name, v)
                applied["world"][var_name] = v
            elif k.startswith("hidden_"):
                var_name = k[7:]
                self.set_hidden_var(var_name, v)
                applied["hidden"][var_name] = v

        return applied
