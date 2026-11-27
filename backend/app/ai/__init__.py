"""Yūgen Mayoiga AI Subsystem.

Provides story context assembly, prompt engineering, LLM provider integration,
structured narrative generation, and AI consistency validation.
"""

from backend.app.ai.action_interpreter import ActionInterpreter
from backend.app.ai.action_validator import (
    DeterministicActionValidator,
    execute_ai_mediated_action,
)
from backend.app.ai.choice_generator import DynamicChoiceGenerator
from backend.app.ai.consistency_checker import ConsistencyChecker, run_deterministic_checks
from backend.app.ai.context_builder import StoryContextBuilder
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AINarrativeError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
)
from backend.app.ai.narrative_generator import NarrativeGenerator
from backend.app.ai.providers import (
    BaseLLMProvider,
    FallbackRouter,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderHealthTracker,
    build_fallback_chain,
    get_default_provider,
)
from backend.app.ai.schemas import (
    AIActionExecutionResponse,
    AIStoryActionRequest,
    ActionInterpretationResult,
    ActionVerb,
    CharacterContext,
    CharacterDialogueSnippet,
    CharacterEmotionContext,
    CharacterTraitsContext,
    CheckStatus,
    ChoiceGenerationStatus,
    ChoiceRiskLevel,
    ConsistencyIssue,
    ConsistencyReport,
    DynamicChoice,
    DynamicChoiceSet,
    HistoryEntryContext,
    InterpretationStatus,
    InterpretedAction,
    IssueCategory,
    IssueSeverity,
    MemoryContext,
    NarrativeGenerationRequest,
    NarrativeGenerationResult,
    NarrativeResponseEnvelope,
    PlayerInputContext,
    RelationshipContext,
    SceneContext,
    StoryAIContext,
    StoryRuntimeContext,
)

__all__ = [
    # Context Builder, Generator, Checker, Choice Gen, Interpreter
    "StoryContextBuilder",
    "NarrativeGenerator",
    "ConsistencyChecker",
    "run_deterministic_checks",
    "DynamicChoiceGenerator",
    "ActionInterpreter",
    "DeterministicActionValidator",
    "execute_ai_mediated_action",
    # Providers
    "BaseLLMProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "FallbackRouter",
    "ProviderHealthTracker",
    "build_fallback_chain",
    "get_default_provider",
    # Schemas — context
    "StoryAIContext",
    "PlayerInputContext",
    "SceneContext",
    "CharacterContext",
    "CharacterEmotionContext",
    "CharacterTraitsContext",
    "RelationshipContext",
    "MemoryContext",
    "HistoryEntryContext",
    "StoryRuntimeContext",
    # Schemas — generation
    "NarrativeGenerationResult",
    "NarrativeGenerationRequest",
    "NarrativeResponseEnvelope",
    "CharacterDialogueSnippet",
    # Schemas — consistency
    "ConsistencyReport",
    "ConsistencyIssue",
    "IssueSeverity",
    "IssueCategory",
    "CheckStatus",
    # Schemas — dynamic choices & action interpretation (Phase 4)
    "DynamicChoice",
    "DynamicChoiceSet",
    "ChoiceRiskLevel",
    "ChoiceGenerationStatus",
    "InterpretedAction",
    "ActionInterpretationResult",
    "InterpretationStatus",
    "ActionVerb",
    "AIStoryActionRequest",
    "AIActionExecutionResponse",
    # Exceptions
    "AINarrativeError",
    "AIConfigurationError",
    "AIProviderError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIResponseValidationError",
    "AIEmptyResponseError",
]


