"""Pydantic schemas for AI context structures used in narrative generation.

These types are the clean, serializable boundary between the deterministic
story engine and the AI subsystem.  No SQLAlchemy objects are exposed here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Player input
# ---------------------------------------------------------------------------


class PlayerInputContext(BaseModel):
    """Captures what the player did to arrive at the current moment."""

    model_config = ConfigDict(str_strip_whitespace=True)

    choice_text: Optional[str] = Field(
        default=None,
        description="Text of the predefined choice the player selected, if any.",
    )
    free_text: Optional[str] = Field(
        default=None,
        description="Raw free-text action the player typed, if any.",
    )
    parsed_action: Optional[str] = Field(
        default=None,
        description="Normalised action verb parsed from free_text by the action pipeline.",
    )


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class SceneContext(BaseModel):
    """Serialisable snapshot of the current scene."""

    model_config = ConfigDict(from_attributes=False)

    id: int
    story_id: int
    scene_number: int
    location: str
    mood: str
    content: str
    haiku: Optional[str] = None
    is_ending: bool


# ---------------------------------------------------------------------------
# Character emotion & traits
# ---------------------------------------------------------------------------


class CharacterEmotionContext(BaseModel):
    """Current Big-Six emotion values for a character (0-100 each)."""

    fear: int = Field(ge=0, le=100)
    anxiety: int = Field(ge=0, le=100)
    anger: int = Field(ge=0, le=100)
    sadness: int = Field(ge=0, le=100)
    happiness: int = Field(ge=0, le=100)
    trust: int = Field(ge=0, le=100)


class CharacterTraitsContext(BaseModel):
    """Big-Five personality traits for a character (0-100 each)."""

    openness: int = Field(ge=0, le=100)
    conscientiousness: int = Field(ge=0, le=100)
    extraversion: int = Field(ge=0, le=100)
    agreeableness: int = Field(ge=0, le=100)
    neuroticism: int = Field(ge=0, le=100)


class CharacterContext(BaseModel):
    """Serialisable snapshot of a single character's state."""

    id: int
    name: str
    role: str
    age: Optional[int] = None
    background: str
    goals: list[Any] = Field(default_factory=list)
    fears: list[Any] = Field(default_factory=list)
    secrets: list[Any] = Field(default_factory=list)
    emotions: CharacterEmotionContext
    traits: Optional[CharacterTraitsContext] = None


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------


class RelationshipContext(BaseModel):
    """Directed relationship between two characters."""

    from_character_id: int
    from_character_name: str
    to_character_id: int
    to_character_name: str
    trust: int = Field(ge=0, le=100)
    friendship: int = Field(ge=0, le=100)
    suspicion: int = Field(ge=0, le=100)
    fear: int = Field(ge=0, le=100)
    dependency: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

MemoryType = Literal["short_term", "long_term", "emotional", "player_choice"]
MemoryStatus = Literal["normal", "cracked", "gilded"]


class MemoryContext(BaseModel):
    """Serialisable memory entry with its retrieval relevance score."""

    id: int
    character_id: int
    character_name: Optional[str] = None
    event: str
    type: MemoryType
    importance: int = Field(ge=0, le=100)
    emotional_weight: int = Field(ge=-100, le=100)
    status: MemoryStatus
    created_turn: int
    relevance_score: float = Field(
        ge=0.0,
        description="Score (0–1+) produced by the memory retrieval algorithm.",
    )


# ---------------------------------------------------------------------------
# History entry
# ---------------------------------------------------------------------------


class HistoryEntryContext(BaseModel):
    """A single turn's player action as recorded in user_choices_log."""

    turn_number: int
    scene_id: int
    scene_location: Optional[str] = None
    choice_text: Optional[str] = None
    free_text: Optional[str] = None
    parsed_action: Optional[str] = None


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------


class StoryRuntimeContext(BaseModel):
    """Snapshot of the deterministic runtime state (read-only for AI)."""

    turn_number: int
    yugen_meter: int = Field(ge=0, le=100)
    hidden_variables: dict[str, Any] = Field(default_factory=dict)
    world_state: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level AI context
# ---------------------------------------------------------------------------


class StoryAIContext(BaseModel):
    """Complete, serialisable context bundle passed to AI narrative components.

    Constructed by ``StoryContextBuilder``.  Contains *no* SQLAlchemy objects
    and is safe to serialise as JSON or inject into an LLM prompt.
    """

    model_config = ConfigDict(str_strip_whitespace=False)

    # Story metadata
    story_id: int
    story_title: str
    story_theme: str
    story_genre: str
    story_tone: str
    story_season: str
    story_length: str
    story_language: str = "English"
    story_status: str

    # Current and previous position
    current_scene: Optional[SceneContext] = None
    previous_scene: Optional[SceneContext] = None

    # Runtime state
    runtime: StoryRuntimeContext

    # Characters (all in story; AI can filter by scene if needed)
    characters: list[CharacterContext] = Field(default_factory=list)

    # Relationships between characters
    relationships: list[RelationshipContext] = Field(default_factory=list)

    # Relevant memories retrieved by the memory engine
    relevant_memories: list[MemoryContext] = Field(default_factory=list)

    # Recent turn history (bounded)
    recent_history: list[HistoryEntryContext] = Field(default_factory=list)

    # Player's action that triggered this context build
    player_input: Optional[PlayerInputContext] = None

    # Configurable limits used during construction (informational)
    memory_limit: int = Field(default=5, ge=1)
    history_limit: int = Field(default=5, ge=1)


# ---------------------------------------------------------------------------
# Narrative generation output (Phase 2)
# ---------------------------------------------------------------------------


class CharacterDialogueSnippet(BaseModel):
    """Spoken dialogue captured within the generated narrative."""

    model_config = ConfigDict(str_strip_whitespace=True)

    character_name: str = Field(
        min_length=1,
        description="Name of the character speaking.",
    )
    dialogue: str = Field(
        min_length=1,
        description="The spoken words.",
    )


class NarrativeGenerationResult(BaseModel):
    """Structured, validated narrative passage produced by the AI generator.

    Contains the prose continuation, atmospheric metadata, optional dialogue
    metadata, and execution telemetry (model, tokens).

    ``extra='forbid'`` ensures that any game-state mutation fields
    hallucinated by an LLM (e.g. ending_trigger, state_changes, yugen_meter)
    are rejected with a ValidationError rather than silently ignored.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", protected_namespaces=())

    narrative_text: str = Field(
        min_length=1,
        description="The primary atmospheric narrative prose continuation.",
    )
    scene_title: Optional[str] = Field(
        default=None,
        description="Optional title or heading for the passage/scene.",
    )
    scene_mood: Optional[str] = Field(
        default=None,
        description="Atmospheric mood reflected in the passage (e.g. 'Tense', 'Melancholic').",
    )
    passage_summary: Optional[str] = Field(
        default=None,
        description="Brief 1-2 sentence synopsis of what occurred in this passage.",
    )
    dialogue: list[CharacterDialogueSnippet] = Field(
        default_factory=list,
        description="Structured dialogue snippets occurring in the passage.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Name of the LLM model that generated this passage.",
    )
    tokens_used: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total tokens reported by the provider, if available.",
    )



# ---------------------------------------------------------------------------
# Consistency checking output (Phase 3)
# ---------------------------------------------------------------------------


class IssueSeverity(str, Enum):
    """Severity level for a detected consistency issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """Category classifying the type of consistency issue detected."""

    WORLD_STATE_CONTRADICTION = "world_state_contradiction"
    CHARACTER_BEHAVIOR_CONTRADICTION = "character_behavior_contradiction"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    LOCATION_CONTINUITY = "location_continuity"
    MEMORY_CONTRADICTION = "memory_contradiction"
    SCENE_CONTINUITY = "scene_continuity"
    FACTUAL_CONTRADICTION = "factual_contradiction"
    OTHER = "other"


class CheckStatus(str, Enum):
    """Overall status of the consistency check run."""

    PASSED = "passed"            # No issues found
    ISSUES_FOUND = "issues_found"  # One or more issues detected
    PARTIAL = "partial"          # Some categories could not be checked
    UNAVAILABLE = "unavailable"  # AI validation layer was unavailable


class ConsistencyIssue(BaseModel):
    """A single detected consistency issue in the generated narrative.

    ``extra='forbid'`` prevents arbitrary data from leaking in from AI output.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: IssueCategory = Field(
        description="Category of inconsistency detected.",
    )
    severity: IssueSeverity = Field(
        description="Severity level of this issue.",
    )
    description: str = Field(
        min_length=1,
        description="Human-readable description of the inconsistency.",
    )
    evidence: str = Field(
        min_length=1,
        description="Exact quote or reference from context or narrative supporting this finding.",
    )
    affected_character_id: Optional[int] = Field(
        default=None,
        description="ID of the character involved, if applicable.",
    )
    affected_location: Optional[str] = Field(
        default=None,
        description="Location name involved in the issue, if applicable.",
    )
    confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence level of this finding (0=very uncertain, 100=definitive).",
    )


class ConsistencyReport(BaseModel):
    """Full consistency evaluation report for a generated narrative passage.

    ``extra='forbid'`` prevents spurious fields from an AI-sourced report
    from being accepted into the structured result.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    is_consistent: bool = Field(
        description="True when no medium/high/critical issues were found.",
    )
    issues: list[ConsistencyIssue] = Field(
        default_factory=list,
        description="All detected consistency issues, sorted by severity descending.",
    )
    overall_confidence: int = Field(
        ge=0,
        le=100,
        description="Aggregate confidence across all checks (0-100).",
    )
    check_status: CheckStatus = Field(
        description="Overall status of the consistency check run.",
    )
    checked_categories: list[IssueCategory] = Field(
        default_factory=list,
        description="Categories that were successfully evaluated.",
    )
    unavailable_categories: list[IssueCategory] = Field(
        default_factory=list,
        description="Categories that could not be checked (e.g. AI unavailable, insufficient context).",
    )
    summary: str = Field(
        min_length=1,
        description="One-sentence summary of the check outcome.",
    )


# ---------------------------------------------------------------------------
# Dynamic AI Choices (Phase 4)
# ---------------------------------------------------------------------------


class ChoiceRiskLevel(str, Enum):
    """Subjective risk / consequence level of a dynamic choice."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChoiceGenerationStatus(str, Enum):
    """Status of the dynamic choice generation run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class DynamicChoice(BaseModel):
    """A contextual, AI-generated suggestion for a player choice.

    This represents a transient option presented to the player alongside
    predefined deterministic choices. It is NOT saved directly to the database
    and MUST be validated through the deterministic pipeline before execution.

    ``extra='forbid'`` prevents LLM-injected mutation payloads.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    choice_id: str = Field(
        min_length=1,
        max_length=50,
        description="Transient unique identifier for this dynamic choice (e.g. dynamic_ai_1).",
    )
    choice_text: str = Field(
        min_length=1,
        max_length=200,
        description="Evocative, natural choice text presented to the player.",
    )
    action_intent: str = Field(
        min_length=1,
        max_length=50,
        description="Normalized primary action verb or intent (e.g. 'inspect', 'speak', 'search').",
    )
    target: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Specific target object, feature, or area involved in the action.",
    )
    approach: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Method or manner of execution (e.g. 'cautiously', 'stealthily').",
    )
    risk_level: Optional[ChoiceRiskLevel] = Field(
        default=ChoiceRiskLevel.LOW,
        description="Perceived danger or consequence level.",
    )
    choice_type: Literal["dynamic_ai", "emergent_fallback"] = Field(
        default="dynamic_ai",
        description="Explicit type flag distinguishing AI choices or emergent fallback from deterministic graph choices.",
    )
    requires_validation: bool = Field(
        default=True,
        description="Always True. AI choices must pass deterministic server-side validation.",
    )
    scene_id: Optional[int] = Field(
        default=None,
        description="The scene ID for which this choice was generated, preventing stale replay.",
    )


class DynamicChoiceSet(BaseModel):
    """Collection of dynamic AI-generated choices returned to the caller.

    ``extra='forbid'`` prevents unexpected metadata injection.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    choices: list[DynamicChoice] = Field(
        default_factory=list,
        description="List of validated, deduplicated dynamic choices.",
    )
    generation_status: ChoiceGenerationStatus = Field(
        description="Status of choice generation (success, partial, failed, unavailable).",
    )
    generation_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Telemetry metadata such as model_name or fallback reasons.",
    )


# ---------------------------------------------------------------------------
# Free-Text Action Interpretation (Phase 4)
# ---------------------------------------------------------------------------


class InterpretationStatus(str, Enum):
    """Outcome of interpreting free-text player input."""

    SUCCESS = "success"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ActionVerb(str, Enum):
    """Standard permitted action verbs recognized by the deterministic gameplay engine."""

    INSPECT = "inspect"
    SPEAK = "speak"
    SEARCH = "search"
    USE = "use"
    MOVE = "move"
    TAKE = "take"
    WAIT = "wait"
    OTHER = "other"


class InterpretedAction(BaseModel):
    """Structured representation of player natural-language input extracted by AI.

    Preserves the verbatim player text and extracts semantic intent, targets,
    and confidence. This representation is purely descriptive and does NOT
    constitute execution authorization.

    ``extra='forbid'`` prevents arbitrary fields from entering the action pipeline.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    original_text: str = Field(
        min_length=1,
        max_length=500,
        description="Verbatim player natural-language input, preserved exactly.",
    )
    action_intent: str = Field(
        min_length=1,
        max_length=50,
        description="Primary action intent verb (e.g. 'inspect', 'speak', 'search', 'use', 'move').",
    )
    target: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Inanimate target object, scenery element, or focal point.",
    )
    approach: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Manner, method, or tone of the action (e.g. 'carefully', 'gently', 'hurriedly').",
    )
    character_target: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of the character targeted by speech or action, if applicable.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional non-state parameters extracted from the prompt.",
    )
    confidence: int = Field(
        ge=0,
        le=100,
        description="AI confidence score in its semantic interpretation (0-100).",
    )
    is_ambiguous: bool = Field(
        default=False,
        description="True if the input is vague, open to multiple interpretations, or contains multiple conflicting actions.",
    )
    clarification_needed: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Helpful, in-character clarification prompt if the action is ambiguous or unsupported.",
    )
    reasoning_summary: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Concise rationale for the interpretation. Never exposes internal system prompts.",
    )
    is_supported: bool = Field(
        default=True,
        description="Whether the interpreted intent is conceptually supported within narrative gameplay.",
    )


class ActionInterpretationResult(BaseModel):
    """Envelope wrapping the outcome of an action interpretation call.

    ``extra='forbid'`` guarantees schema hygiene.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    interpreted_action: Optional[InterpretedAction] = Field(
        default=None,
        description="The structured interpreted action, if interpretation succeeded.",
    )
    status: InterpretationStatus = Field(
        description="High-level interpretation outcome status.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Human-readable description of provider or validation failures.",
    )


class AIStoryActionRequest(BaseModel):
    """Payload for submitting an AI dynamic choice or free-text action."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    free_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Natural language action typed by the player.",
    )
    dynamic_choice: Optional[DynamicChoice] = Field(
        default=None,
        description="An AI-generated dynamic choice selected by the player.",
    )
    character_id: Optional[int] = Field(
        default=None,
        description="Character executing the action, defaulting to primary character.",
    )


class AIActionExecutionResponse(BaseModel):
    """Structured response returned after processing an AI-mediated action."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Literal["executed", "ambiguous", "rejected", "unavailable"] = Field(
        description="Execution status of the submitted action.",
    )
    interpretation: Optional[InterpretedAction] = Field(
        default=None,
        description="Extracted interpretation, present if free text was analyzed.",
    )
    story_action_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="The deterministic state update result from process_story_action, if executed.",
    )
    clarification_needed: Optional[str] = Field(
        default=None,
        description="Clarification message if the action was ambiguous or incomplete.",
    )
    validation_error: Optional[str] = Field(
        default=None,
        description="Reason the action was rejected by deterministic validation.",
    )


class NarrativeGenerationRequest(BaseModel):
    """Optional player input context payload for narrative continuation generation."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    choice_text: Optional[str] = Field(
        default=None,
        description="Text of the choice that was just executed.",
    )
    free_text: Optional[str] = Field(
        default=None,
        description="Text of the free-form action that was just executed.",
    )


class NarrativeResponseEnvelope(BaseModel):
    """Response envelope containing the generated narrative continuation and advisory consistency report."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Literal["success", "unavailable", "failed"] = Field(
        default="success",
        description="Outcome status of the narrative generation request.",
    )
    narrative: Optional[NarrativeGenerationResult] = Field(
        default=None,
        description="Generated narrative passage, if successful.",
    )
    consistency: Optional[ConsistencyReport] = Field(
        default=None,
        description="Advisory consistency report evaluating the passage against story context.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if generation was unavailable or failed.",
    )


