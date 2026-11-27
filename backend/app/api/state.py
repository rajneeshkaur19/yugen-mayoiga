"""State and story action API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.ai.action_interpreter import ActionInterpreter
from backend.app.ai.action_validator import execute_ai_mediated_action
from backend.app.ai.choice_generator import DynamicChoiceGenerator
from backend.app.ai.consistency_checker import ConsistencyChecker
from backend.app.ai.context_builder import StoryContextBuilder
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AINarrativeError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from backend.app.ai.narrative_generator import NarrativeGenerator
from backend.app.ai.schemas import (
    AIActionExecutionResponse,
    AIStoryActionRequest,
    ActionInterpretationResult,
    ChoiceGenerationStatus,
    ChoiceRiskLevel,
    DynamicChoice,
    DynamicChoiceSet,
    NarrativeGenerationRequest,
    NarrativeResponseEnvelope,
    PlayerInputContext,
)
from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.state import (
    StoryActionRequest,
    StoryActionResponse,
    StoryStateRead,
    YugenMeterRead,
)
from backend.app.core.timing import logger, pipeline_timer
from backend.app.services.action_pipeline import process_story_action
from backend.app.services.choice_service import list_choices
from backend.app.services.state_service import (
    get_or_create_story_state,
    get_unified_story_state,
)
from backend.app.services.story_service import get_story

router = APIRouter(prefix="/stories/{story_id}", tags=["Story State & Action Engine"])


def _require_user_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.get("/state", response_model=StoryStateRead)
def get_story_runtime_state(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full runtime narrative state (visible emotions, world state, relationships, turn, Yūgen Meter)."""
    _require_user_story(story_id, current_user, db)
    unified = get_unified_story_state(db, story_id, include_hidden=False)
    return unified


@router.post("/choice", response_model=StoryActionResponse)
def submit_story_choice(
    story_id: int,
    action_data: StoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a story button choice or action through the integrated deterministic pipeline."""
    _require_user_story(story_id, current_user, db)
    try:
        return process_story_action(
            db=db,
            user_id=current_user.id,
            story_id=story_id,
            choice_id=action_data.choice_id,
            free_text=action_data.free_text,
            active_character_id=action_data.character_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/action", response_model=StoryActionResponse)
def submit_story_action(
    story_id: int,
    action_data: StoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a story free-text action or choice through the integrated pipeline."""
    return submit_story_choice(story_id, action_data, db, current_user)


@router.get("/yugen-meter", response_model=YugenMeterRead)
def get_story_yugen_meter(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve current Yūgen Meter value (0-100) reflecting unresolved mystery."""
    _require_user_story(story_id, current_user, db)
    state = get_or_create_story_state(db, story_id)
    val = state.yugen_meter

    if val >= 75:
        desc = "Deep obscurity; profound mysteries linger unrevealed."
    elif val >= 40:
        desc = "Veiled truth; clues have begun to surface."
    else:
        desc = "Clarity dawns; the core mystery has been largely unveiled."

    return {
        "story_id": story_id,
        "yugen_meter": val,
        "mystery_description": desc,
    }


# In-memory scene choice cache to prevent unnecessary duplicate AI calls when scene has not changed
# Keys supported: (story_id, scene_id) or (story_id, scene_id, turn_number)
_SCENE_CHOICE_CACHE: dict[tuple, DynamicChoiceSet] = {}


@router.get("/dynamic-choices", response_model=DynamicChoiceSet)
def get_dynamic_choices(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate context-aware dynamic AI choices for the story's current scene."""
    _require_user_story(story_id, current_user, db)
    with pipeline_timer("Dynamic Choice Retrieval Endpoint", {"story_id": story_id}) as endpoint_timer:
        story_state = get_or_create_story_state(db, story_id, commit=True)
        turn_num = story_state.turn_number if story_state else 1
        current_scene_id = story_state.current_scene_id or 0
        endpoint_timer["scene_id"] = current_scene_id
        endpoint_timer["turn"] = turn_num

        # Check turn-level cache first (reusing choices within same scene and turn)
        turn_cache_key = (story_id, current_scene_id, turn_num)
        cached = _SCENE_CHOICE_CACHE.get(turn_cache_key)
        if cached is not None and cached.generation_status == "success" and cached.choices:
            endpoint_timer["cached"] = True
            endpoint_timer["choices_count"] = len(cached.choices)
            return cached

        # Check if current scene is an ending scene (no choices required)
        context_builder = StoryContextBuilder(db)
        context = context_builder.build(story_id=story_id, memory_limit=2, history_limit=2)

        if context.current_scene and context.current_scene.is_ending:
            empty_set = DynamicChoiceSet(
                choices=[],
                generation_status="success",
                generation_metadata={"reason": "Ending scene reached; no emergent paths."},
            )
            _SCENE_CHOICE_CACHE[scene_cache_key] = empty_set
            endpoint_timer["ending_scene"] = True
            return empty_set

        # Fetch existing deterministic choices to prevent duplicate suggestions
        active_scene_id = context.current_scene.id if context.current_scene else current_scene_id
        existing_choices = list_choices(db, story_id=story_id, scene_id=active_scene_id)
        existing_texts = [c.choice_text for c in existing_choices]

        generator = DynamicChoiceGenerator()
        result = generator.generate_choices(
            context=context,
            existing_choices=existing_texts,
            max_choices=3,
        )
        if result.generation_status != ChoiceGenerationStatus.SUCCESS or not result.choices:
            loc = context.current_scene.location if context.current_scene else "surroundings"
            fallback_choices = [
                DynamicChoice(
                    choice_id="emergent_fb_1",
                    choice_text=f"Examine the {loc} closely for obscured markings or subtle clues.",
                    action_intent="inspect",
                    target=loc,
                    approach="cautiously",
                    risk_level=ChoiceRiskLevel.LOW,
                    choice_type="emergent_fallback",
                    requires_validation=True,
                    scene_id=active_scene_id,
                ),
                DynamicChoice(
                    choice_id="emergent_fb_2",
                    choice_text="Pause in the stillness and listen for distant echoes in the mist.",
                    action_intent="listen",
                    target="mist",
                    approach="quietly",
                    risk_level=ChoiceRiskLevel.LOW,
                    choice_type="emergent_fallback",
                    requires_validation=True,
                    scene_id=active_scene_id,
                ),
            ]
            result = DynamicChoiceSet(
                choices=fallback_choices,
                generation_status=ChoiceGenerationStatus.SUCCESS,
                generation_metadata={
                    "fallback": True,
                    "reason": result.generation_metadata.get("error", "AI service fallback active"),
                },
            )

        if result.generation_status == ChoiceGenerationStatus.SUCCESS and result.choices:
            _SCENE_CHOICE_CACHE[turn_cache_key] = result
            # Evict older turn cache for this story
            stale_keys = [k for k in list(_SCENE_CHOICE_CACHE.keys()) if k[0] == story_id and len(k) > 2 and k[2] < turn_num]
            for sk in stale_keys:
                _SCENE_CHOICE_CACHE.pop(sk, None)

        endpoint_timer["cached"] = False
        endpoint_timer["choices_count"] = len(result.choices)
        return result


@router.post("/interpret-action", response_model=ActionInterpretationResult)
def interpret_player_action(
    story_id: int,
    action_data: StoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Interpret natural-language player input into structured semantic intent without executing state changes."""
    _require_user_story(story_id, current_user, db)
    if not action_data.free_text or not action_data.free_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="free_text is required for action interpretation.",
        )

    context_builder = StoryContextBuilder(db)
    context = context_builder.build(story_id=story_id)

    interpreter = ActionInterpreter()
    return interpreter.interpret(
        context=context,
        player_text=action_data.free_text.strip(),
    )


@router.post("/ai-action", response_model=AIActionExecutionResponse)
def submit_ai_story_action(
    story_id: int,
    action_data: AIStoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a free-text action or dynamic choice with AI interpretation and deterministic validation."""
    _require_user_story(story_id, current_user, db)
    try:
        return execute_ai_mediated_action(
            db=db,
            user_id=current_user.id,
            story_id=story_id,
            action_request=action_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/generate-narrative", response_model=NarrativeResponseEnvelope)
def generate_story_narrative(
    story_id: int,
    request_data: Optional[NarrativeGenerationRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an AI narrative continuation and consistency check for the current story state."""
    _require_user_story(story_id, current_user, db)
    with pipeline_timer("Narrative Endpoint Request", {"story_id": story_id}) as req_timer:
        get_or_create_story_state(db, story_id, commit=True)

        player_input = None
        if request_data:
            player_input = PlayerInputContext(
                choice_text=request_data.choice_text,
                free_text=request_data.free_text,
            )

        context_builder = StoryContextBuilder(db)
        context = context_builder.build(
            story_id=story_id,
            player_input=player_input,
            memory_limit=2,
            history_limit=2,
        )

        generator = NarrativeGenerator()
        try:
            narrative_result = generator.generate_narrative(context)
            req_timer["status"] = "success"
        except (AIConfigurationError, AITimeoutError, AIRateLimitError, AIProviderError, AINarrativeError) as exc:
            req_timer["status"] = "unavailable"
            req_timer["error"] = str(exc)
            return NarrativeResponseEnvelope(
                status="unavailable",
                narrative=None,
                consistency=None,
                error_message=f"AI narrative generator unavailable: {exc}",
            )
        except Exception as exc:
            req_timer["status"] = "failed"
            req_timer["error"] = str(exc)
            return NarrativeResponseEnvelope(
                status="failed",
                narrative=None,
                consistency=None,
                error_message=f"Narrative generation failed: {exc}",
            )

        # Advisory consistency check (deterministic to conserve API quota per requirement 8)
        checker = ConsistencyChecker(skip_ai_check=True)
        consistency_report = None
        try:
            consistency_report = checker.check(context, narrative_result)
        except Exception:
            pass

        return NarrativeResponseEnvelope(
            status="success",
            narrative=narrative_result,
            consistency=consistency_report,
            error_message=None,
        )


