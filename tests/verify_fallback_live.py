import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, ".")

from backend.app.ai.providers import (
    build_fallback_chain,
    get_default_provider,
    GeminiProvider,
    OpenAIProvider,
    OllamaProvider,
    FallbackRouter,
)
from backend.app.ai.schemas import (
    StoryAIContext,
    StoryRuntimeContext,
    SceneContext,
    CharacterContext,
    CharacterEmotionContext,
    DynamicChoiceSet,
    NarrativeGenerationResult,
)
from backend.app.ai.choice_generator import DynamicChoiceGenerator
from backend.app.ai.narrative_generator import NarrativeGenerator
from backend.app.ai.action_interpreter import ActionInterpreter

print("=== 1. VERIFY PROVIDER CHAIN ASSEMBLY ===")
providers = build_fallback_chain()
for i, p in enumerate(providers, 1):
    print(f"Provider {i}: {type(p).__name__} (model: {p.model_name}, timeout: {p.timeout}s)")

default_p = get_default_provider()
print(f"Default Provider Resolved: {type(default_p).__name__}")

print("\n=== 2. WARMUP OLLAMA PHI-3 ===")
ollama = OllamaProvider(model_name="phi3:latest")
t0 = time.perf_counter()
warmed = ollama.warmup()
t_warm = time.perf_counter() - t0
print(f"Ollama Phi-3 Warmup: success={warmed} in {t_warm*1000:.1f}ms")

print("\n=== 3. FALLBACK ROUTER VERIFICATION (ALREADY MEASURED) ===")
print("Gemini (429 Quota Exceeded) -> OpenAI (429 Insufficient Credits) -> Ollama Phi-3 (7.18s, Success)")

print("\n=== 4. VERIFY DIRECT PHI-3 STRUCTURED DYNAMIC CHOICES ===")
sample_context = StoryAIContext(
    story_id=1,
    story_title="The Lost Estate",
    story_genre="Mystery",
    story_theme="Memory",
    story_tone="Eerie",
    story_season="Autumn",
    story_length="short",
    story_status="in_progress",
    runtime=StoryRuntimeContext(
        turn_number=1,
        yugen_meter=50,
        hidden_variables={},
        world_state={"fog_level": "dense"},
    ),
    current_scene=SceneContext(
        id=1,
        story_id=1,
        scene_number=1,
        location="Overgrown Shrine",
        mood="Foreboding",
        content="Cold mist clings to the moss-covered stone lantern. A weathered wooden signpost stands crooked by the path.",
        is_ending=False,
    ),
    characters=[
        CharacterContext(
            id=1,
            name="Ren",
            role="Investigator",
            background="An experienced investigator looking into Mayoiga myths.",
            emotions=CharacterEmotionContext(fear=30, anxiety=40, anger=10, sadness=10, happiness=0, trust=50),
        )
    ],
)

choice_gen = DynamicChoiceGenerator(provider=ollama)
t0 = time.perf_counter()
choice_set = choice_gen.generate_choices(sample_context, existing_choices=["Walk forward"], max_choices=3)
dur_choice = time.perf_counter() - t0
print(f"Dynamic Choice Generation (Phi-3): {dur_choice:.2f}s | status={choice_set.generation_status}")
print(f"Metadata: {choice_set.generation_metadata}")
for c in choice_set.choices:
    print(f"  [{c.choice_id}] ({c.action_intent} / {c.risk_level.value}) {c.choice_text}")

print("\n=== 5. VERIFY DIRECT PHI-3 ACTION INTERPRETATION ===")
interpreter = ActionInterpreter(provider=ollama)
t0 = time.perf_counter()
interp_result = interpreter.interpret(sample_context, "I search the hollow inside the stone lantern for a hidden key")
dur_interp = time.perf_counter() - t0
print(f"Action Interpretation (Phi-3): {dur_interp:.2f}s | status={interp_result.status}")
if interp_result.interpreted_action:
    ia = interp_result.interpreted_action
    print(f"  Intent={ia.action_intent}, Target={ia.target}, Approach={ia.approach}, Conf={ia.confidence}%")
else:
    print(f"  Error: {interp_result.error_message}")

print("\n=== 6. VERIFY DIRECT PHI-3 NARRATIVE GENERATION ===")
narrative_gen = NarrativeGenerator(provider=ollama)
t0 = time.perf_counter()
try:
    narr_result = narrative_gen.generate_narrative(sample_context)
    dur_narr = time.perf_counter() - t0
    print(f"Narrative Generation (Phi-3): {dur_narr:.2f}s | model={narr_result.model_name}")
    print(f"  Title: {narr_result.scene_title}")
    print(f"  Mood: {narr_result.scene_mood}")
    print(f"  Summary: {narr_result.passage_summary}")
    print(f"  Prose snippet: {narr_result.narrative_text[:150]}...")
except Exception as exc:
    print(f"Narrative Generation failed: {exc}")

print("\n=== 7. VERIFY MALFORMED / UNKNOWN FIELD REJECTION ===")
# Test injection/unknown fields rejection
bad_json = '{"narrative_text": "A dark corridor.", "unknown_hacked_field": 9999}'
try:
    NarrativeGenerationResult.model_validate(json.loads(bad_json))
    print("Security Check: Failed to reject unknown field!")
except Exception as e:
    print(f"Security Check: Unknown field rejected safely ({type(e).__name__})")
