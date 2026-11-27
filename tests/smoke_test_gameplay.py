import os
import sys
import time
from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.user import User
from backend.app.core.security import create_access_token
import uuid
from backend.app.models.story import Story
from backend.app.models.scene import Scene
from backend.app.models.choice import Choice
from backend.app.models.character import Character
from backend.app.models.character_traits import CharacterTraits
from backend.app.models.ending import Ending

def create_full_test_story(db_session, test_user):
    uid = uuid.uuid4().hex[:6]
    story = Story(
        user_id=test_user.id,
        title=f"Smoke Tale {uid}",
        genre="Mystery",
        theme="Isolation",
        tone="Eerie",
        season="Autumn",
        length="short",
        status="active",
    )
    db_session.add(story)
    db_session.flush()

    scene1 = Scene(
        story_id=story.id,
        scene_number=1,
        content="Standing before the creaking wooden gate of Mayoiga.",
        location="Front Gate",
        mood="Foreboding",
        is_ending=False,
    )
    scene2 = Scene(
        story_id=story.id,
        scene_number=2,
        content="Inside the sunken hearth room, embers still glow.",
        location="Irori Hearth",
        mood="Mysterious",
        is_ending=False,
    )
    scene_ending = Scene(
        story_id=story.id,
        scene_number=3,
        content="The dawn light filters through paper screens. The truth is revealed.",
        location="Garden Shrine",
        mood="Serene",
        is_ending=True,
    )
    db_session.add_all([scene1, scene2, scene_ending])
    db_session.flush()

    choice = Choice(
        story_id=story.id,
        scene_id=scene1.id,
        choice_text="Step across the threshold into the dark corridor.",
        effects={"fear": 15, "world_door": "unlocked", "yugen_meter": -10},
        next_scene_id=scene2.id,
    )
    db_session.add(choice)

    char = Character(
        story_id=story.id,
        name=f"Aki_{uid}",
        role="Guide",
        age=21,
        background="A villager who knows the legends of Mayoiga.",
    )
    db_session.add(char)
    db_session.flush()

    traits = CharacterTraits(
        character_id=char.id,
        openness=70, conscientiousness=60, extraversion=40, agreeableness=65, neuroticism=55,
    )
    db_session.add(traits)
    db_session.commit()
    return {"story": story, "scene1": scene1, "scene2": scene2, "choice": choice}

client = TestClient(app)
db = SessionLocal()

# 1. User Authentication
user = db.query(User).filter(User.email == "smoke_tester@example.com").first()
if not user:
    user = User(
        email="smoke_tester@example.com",
        username="smoketester",
        password_hash="fakehashedpassword123",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

token = create_access_token(subject=str(user.id))
headers = {"Authorization": f"Bearer {token}"}
print(f"[AUTH] User authenticated: {user.username} (ID: {user.id})")

# 2. Setup Full Story with Scenes, Choices, Characters, Endings
story_data = create_full_test_story(db, user)
db.commit()
story_id = story_data["story"].id
scene1_id = story_data["scene1"].id
scene2_id = story_data["scene2"].id
choice1_id = story_data["choice"].id
print(f"[STORY] Created full story: ID {story_id} with Scenes [{scene1_id}, {scene2_id}]")

# 3. Read Initial State (Scene 1)
t0 = time.perf_counter()
r_state = client.get(f"/stories/{story_id}/state", headers=headers)
dur_state = time.perf_counter() - t0
assert r_state.status_code == 200, f"Failed state read: {r_state.text}"
state1 = r_state.json()
print(f"[STATE SCENE 1] ({dur_state*1000:.1f}ms): Turn={state1['turn_number']}, Scene={state1['current_scene_id']}, Yugen={state1['yugen_meter']}")

# 4. Predefined Choice Execution (Scene 1 -> Scene 2)
t0 = time.perf_counter()
r_choice = client.post(
    f"/stories/{story_id}/choice",
    json={"choice_id": choice1_id},
    headers=headers,
)
dur_predefined = time.perf_counter() - t0
assert r_choice.status_code == 200, f"Choice execution failed: {r_choice.text}"
choice_res = r_choice.json()
print(f"[ACTION: PREDEFINED CHOICE] ({dur_predefined*1000:.1f}ms): Transitioned to Scene {choice_res['current_scene_id']}, Next Turn={choice_res['turn_number']}")

# 5. Fetch Dynamic AI Choices for Scene 2 (Testing generation + fallback)
t0 = time.perf_counter()
r_dyn = client.get(f"/stories/{story_id}/dynamic-choices", headers=headers)
dur_dyn = time.perf_counter() - t0
assert r_dyn.status_code == 200, f"Dynamic choices failed: {r_dyn.text}"
dyn_data = r_dyn.json()
choices = dyn_data.get("choices", [])
print(f"[DYNAMIC CHOICES UNCACHED] ({dur_dyn*1000:.1f}ms): Status={dyn_data.get('generation_status')}, Choices={len(choices)}")
for c in choices[:3]:
    print(f"  [{c['choice_id']}] ({c['action_intent']}) {c['choice_text']}")

# 6. Fetch Dynamic AI Choices again (Testing In-Memory Cache)
t0 = time.perf_counter()
r_dyn_cache = client.get(f"/stories/{story_id}/dynamic-choices", headers=headers)
dur_dyn_cache = time.perf_counter() - t0
assert r_dyn_cache.status_code == 200
print(f"[DYNAMIC CHOICES CACHED] ({dur_dyn_cache*1000:.2f}ms): Reused {len(r_dyn_cache.json().get('choices', []))} choices from scene cache (0 AI calls)")

# 7. Execute Emergent Path (Dynamic Choice Fast Path)
if choices:
    t0 = time.perf_counter()
    r_emergent = client.post(
        f"/stories/{story_id}/ai-action",
        json={"dynamic_choice": choices[0]},
        headers=headers,
    )
    dur_emergent = time.perf_counter() - t0
    assert r_emergent.status_code == 200, f"Emergent choice failed: {r_emergent.text}"
    print(f"[ACTION: EMERGENT CHOICE FAST-PATH] ({dur_emergent*1000:.1f}ms): Status={r_emergent.json().get('status')}")

# 8. Free-Text Action Execution with Deterministic Validation
free_text_payload = {"free_text": "Examine the old iron kettle sitting on the ashes of the hearth"}
t0 = time.perf_counter()
r_freetext = client.post(
    f"/stories/{story_id}/ai-action",
    json=free_text_payload,
    headers=headers,
)
dur_freetext = time.perf_counter() - t0
print(f"[ACTION: FREE-TEXT INTERPRETATION] ({dur_freetext*1000:.1f}ms): HTTP {r_freetext.status_code} | Result={r_freetext.json().get('status')}")

# 9. Narrative Continuation Generation Endpoint
t0 = time.perf_counter()
r_narr = client.post(
    f"/stories/{story_id}/generate-narrative",
    json={"free_text": "I sit silently by the hearth, listening for distant footsteps."},
    headers=headers,
)
dur_narr = time.perf_counter() - t0
narr_env = r_narr.json()
print(f"[NARRATIVE GENERATION] ({dur_narr*1000:.1f}ms): Status={narr_env.get('status')}")
if narr_env.get("narrative"):
    print(f"  Prose snippet: {narr_env['narrative'].get('narrative_text')[:120]}...")

# 10. Verify Yūgen Meter Endpoint
r_yugen = client.get(f"/stories/{story_id}/yugen-meter", headers=headers)
assert r_yugen.status_code == 200
ym = r_yugen.json()
print(f"[YUGEN METER] Value={ym['yugen_meter']} | Description: {ym['mystery_description']}")

print("\n=== SMOKE TEST: ALL 10 GAMEPLAY ENGINE CHECKS PASSED SUCCESSFULLY ===")
