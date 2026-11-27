"""End-to-end live gameplay test verifying the complete new story lifecycle:
1. Authentication
2. Environmental Image Generation with fallback
3. Story Creation with full 9-scene graph
4. Initial choice verification (3 initial choices, not 2)
5. Dynamic choice generation with fallback
6. Multi-turn gameplay progression across connected scenes
7. Verification that story does NOT prematurely end
8. Verification that story legitimately completes only at the final ending scene
"""

import httpx
import time

BASE_URL = "http://127.0.0.1:8000"

def test_full_gameplay_flow():
    print("=== Step 1: Authenticate ===")
    t0 = time.time()
    login_resp = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": "testplayer@example.com", "password": "Password123!"},
        timeout=10,
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Authenticated successfully in {time.time() - t0:.3f}s")

    print("\n=== Step 2: Environmental Image Generation (Imagen 3 / Fallback) ===")
    t0 = time.time()
    img_resp = httpx.post(
        f"{BASE_URL}/ai/generate-location-image",
        headers=headers,
        json={
            "name": "Shrouded Torii Pavilion",
            "atmosphere": "Sacred mist and amber lantern glow",
            "description": "An ancient wooden pavilion by a mountain stream.",
            "visual_details": "Stone lanterns, mossy steps, drifting fog",
        },
        timeout=20,
    )
    assert img_resp.status_code == 200, f"Image gen HTTP error: {img_resp.text}"
    img_data = img_resp.json()
    print(f"Image API response ({time.time() - t0:.3f}s): success={img_data['success']}, provider={img_data['provider']}")
    print(f"Image URL: {img_data['image_url']}")
    assert img_data["success"] is True
    assert img_data["image_url"] is not None

    print("\n=== Step 3: Create Story Chronicle ===")
    t0 = time.time()
    story_resp = httpx.post(
        f"{BASE_URL}/stories",
        headers=headers,
        json={
            "title": "The Whisper of Cedar",
            "genre": "Psychological Mystery",
            "theme": "A wanderer returns to an abandoned mountain shrine seeking forgotten truths.",
            "tone": "Eerie and Atmospheric",
            "season": "Autumn",
            "length": "medium",
        },
        timeout=10,
    )
    assert story_resp.status_code == 201, f"Story create failed: {story_resp.text}"
    story = story_resp.json()
    story_id = story["id"]
    print(f"Story created: id={story_id}, title='{story['title']}' in {time.time() - t0:.3f}s")

    print("\n=== Step 4: Populate Rich 9-Scene Graph ===")
    scene_defs = [
        {
            "key": "start",
            "scene_number": 1,
            "location": "Shrouded Torii Pavilion",
            "mood": "Eerie and atmospheric",
            "content": "Autumn mist descends heavily over Shrouded Torii Pavilion. A single lantern flickers beneath the weathered cedar eaves. On a low cedar table rests an unopened envelope sealed with crimson wax. Somewhere beyond the garden, a temple bell rings once.",
            "haiku": "Mist gathers the past\nA lantern guards the silence\nFootsteps seek the truth",
            "is_ending": False,
        },
        {
            "key": "west_wing",
            "scene_number": 2,
            "location": "The Western Corridor",
            "mood": "Uneasy and nostalgic",
            "content": "The wooden floorboards whisper softly beneath your steps. A cracked timetable hangs beside a tarnished mirror. Tucked behind the frame, you discover an old photograph of someone whose eyes seem hauntingly familiar: 'Some thresholds unlock only when remembered.'",
            "haiku": "Beneath fading signs\nOld memories stir below\nThe dark holds its breath",
            "is_ending": False,
        },
        {
            "key": "hearth_room",
            "scene_number": 3,
            "location": "The Hearth Chamber",
            "mood": "Intimate and veiled",
            "content": "Embers pulse with gentle warmth inside the sunken irori hearth. As you unfold the parchment beside the fire, the script recounts a vow made here decades ago. A small brass crane key slips from the envelope.",
            "haiku": "A letter unfolds\nThe past waits in the shadows\nOne key turns slowly",
            "is_ending": False,
        },
        {
            "key": "perimeter_garden",
            "scene_number": 4,
            "location": "The Boundary Garden",
            "mood": "Quiet and contemplative",
            "content": "Cold night air carries the scent of pine needles and damp moss. A stone lantern guides you along a winding gravel path beside a still reflection pond.",
            "haiku": "Rain on stone pathways\nWater mirrors quiet skies\nTwo paths wait ahead",
            "is_ending": False,
        },
        {
            "key": "cellar_archive",
            "scene_number": 5,
            "location": "The Shadowed Archive",
            "mood": "Suspenseful and revelatory",
            "content": "Stone steps descend into a quiet chamber carved into bedrock. Shelves of hand-bound chronicles and lineage scrolls line the walls. An open journal on a pedestal confirms this haven has waited for your return.",
            "haiku": "Ink on ancient scrolls\nThe lineage of silence\nTruth awakens here",
            "is_ending": False,
        },
        {
            "key": "inner_sanctum",
            "scene_number": 6,
            "location": "The Inner Sanctum",
            "mood": "Profound and resonant",
            "content": "You step into a grand hall of tatami and polished cedar beams. At the altar, paper lanterns begin to glow with warm luminescence as you cross the threshold.",
            "haiku": "Lanterns bloom in dark\nA choice echoes in the hall\nDawn awaits your word",
            "is_ending": False,
        },
        {
            "key": "ending_truth",
            "scene_number": 7,
            "location": "The Unveiled Dawn",
            "mood": "Serene and transcendent",
            "content": "Dawn breaks across the mountain ridge, scattering the fog into gold. The mysteries have become part of who you are. You return to the waking world with a heart at peace.",
            "haiku": "Dawn touches the eaves\nA quiet truth finds its home\nThe bell tolls no more",
            "is_ending": True,
        },
        {
            "key": "ending_eternal",
            "scene_number": 8,
            "location": "The Timeless Sanctuary",
            "mood": "Mystical and eternal",
            "content": "The warmth of the irori hearth spreads throughout the ancient estate. Mayoiga has found its protector, and you have found your home.",
            "haiku": "Silver mists draw near\nThe hearth burns with steady warmth\nHome is found at last",
            "is_ending": True,
        },
        {
            "key": "ending_twilight",
            "scene_number": 9,
            "location": "Where the Mists Dissolve",
            "mood": "Melancholic and contemplative",
            "content": "You stand at the boundary torii gate as twilight yields to morning grey. Behind you, the lights fade into mist. Your journey ends here, but its echo remains yours.",
            "haiku": "Footsteps fade away\nA memory in the fog\nThe mountain stays still",
            "is_ending": True,
        },
    ]

    scene_map = {}
    for sc in scene_defs:
        key = sc.pop("key")
        res = httpx.post(f"{BASE_URL}/stories/{story_id}/scenes", headers=headers, json=sc, timeout=10)
        assert res.status_code == 201, f"Failed creating scene {key}: {res.text}"
        scene_map[key] = res.json()["id"]

    print(f"Created {len(scene_map)} scenes successfully. Scene IDs: {scene_map}")

    # Choice links
    choice_links = [
        {"from": "start", "to": "west_wing", "text": "Follow the distant temple bell deeper toward the western wing.", "order": 0},
        {"from": "start", "to": "hearth_room", "text": "Open the wax-sealed letter beside the glowing embers.", "order": 1},
        {"from": "start", "to": "perimeter_garden", "text": "Step out onto the mossy engawa and scout the misty grounds.", "order": 2},

        {"from": "west_wing", "to": "cellar_archive", "text": "Descend the narrow staircase into the shadowed cellar archives.", "order": 0},
        {"from": "west_wing", "to": "hearth_room", "text": "Carry the old photograph toward the warmth of the hearth chamber.", "order": 1},

        {"from": "hearth_room", "to": "cellar_archive", "text": "Search for where the brass crane key was forged in the lower archives.", "order": 0},
        {"from": "hearth_room", "to": "perimeter_garden", "text": "Take a bronze lantern out into the boundary gardens.", "order": 1},

        {"from": "perimeter_garden", "to": "cellar_archive", "text": "Inspect the stone foundation and enter the lower archive entrance.", "order": 0},
        {"from": "perimeter_garden", "to": "inner_sanctum", "text": "Cross the arched bridge toward the glowing inner sanctum.", "order": 1},

        {"from": "cellar_archive", "to": "inner_sanctum", "text": "Ascend into the inner sanctum to confront the core truth of Mayoiga.", "order": 0},
        {"from": "cellar_archive", "to": "perimeter_garden", "text": "Return to the open air and ponder the weight of the family scrolls.", "order": 1},

        {"from": "inner_sanctum", "to": "ending_truth", "text": "Unseal the sanctuary boundary and return to the waking world with peace.", "order": 0},
        {"from": "inner_sanctum", "to": "ending_eternal", "text": "Ignite the central keeper flame and accept your stewardship of Mayoiga.", "order": 1},
        {"from": "inner_sanctum", "to": "ending_twilight", "text": "Leave an offering upon the altar and walk quietly into the dawn mist.", "order": 2},
    ]

    for cl in choice_links:
        from_id = scene_map[cl["from"]]
        to_id = scene_map[cl["to"]]
        c_res = httpx.post(
            f"{BASE_URL}/stories/{story_id}/scenes/{from_id}/choices",
            headers=headers,
            json={
                "choice_text": cl["text"],
                "effects": {"yugen_meter": 5},
                "condition": None,
                "allow_loop": False,
                "sort_order": cl["order"],
                "next_scene_id": to_id,
            },
            timeout=10,
        )
        assert c_res.status_code == 201, f"Failed choice link {cl['text']}: {c_res.text}"

    print(f"Created {len(choice_links)} choices across the graph.")

    print("\n=== Step 5: Verify Initial Scene 1 and Available Choices ===")
    state_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/state", headers=headers, timeout=10)
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["current_scene_id"] == scene_map["start"]
    assert state["turn_number"] == 0

    choices_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/scenes/{scene_map['start']}/choices", headers=headers, timeout=10)
    initial_choices = choices_resp.json()
    print(f"Initial deterministic choices count: {len(initial_choices)} (Expected 3)")
    assert len(initial_choices) == 3, f"Expected 3 choices, got {len(initial_choices)}"
    for idx, c in enumerate(initial_choices, 1):
        print(f"  Choice {idx}: '{c['choice_text']}' -> next_scene_id={c['next_scene_id']}")

    print("\n=== Step 6: Verify Dynamic AI Choices / Fallback ===")
    t0 = time.time()
    dyn_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/dynamic-choices", headers=headers, timeout=25)
    assert dyn_resp.status_code == 200
    dyn_data = dyn_resp.json()
    print(f"Dynamic choices status: {dyn_data['generation_status']} in {time.time() - t0:.2f}s")
    print(f"Dynamic choices count: {len(dyn_data['choices'])}")
    assert len(dyn_data["choices"]) > 0, "Expected dynamic choices to be present"
    for c in dyn_data["choices"]:
        print(f"  Dynamic choice: '{c['choice_text']}' ({c['choice_type']})")

    print("\n=== Step 7: Turn 1 -> Select Choice 1 (Advance to Scene 2: The Western Corridor) ===")
    action_1 = httpx.post(
        f"{BASE_URL}/stories/{story_id}/choice",
        headers=headers,
        json={"choice_id": initial_choices[0]["id"]},
        timeout=10,
    )
    assert action_1.status_code == 200
    res_1 = action_1.json()
    print(f"Turn 1 Result: current_scene_id={res_1['current_scene_id']} (Expected {scene_map['west_wing']})")
    print(f"Turn Number: {res_1['turn_number']}, Location: '{res_1['scene_location']}', is_ending={res_1['is_ending']}")
    assert res_1["current_scene_id"] == scene_map["west_wing"]
    assert res_1["is_ending"] is False
    assert res_1["turn_number"] == 1

    print("\n=== Step 8: Turn 2 -> Select Choice from Scene 2 (Advance to Scene 5: The Shadowed Archive) ===")
    c2_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/scenes/{scene_map['west_wing']}/choices", headers=headers, timeout=10)
    sc2_choices = c2_resp.json()
    print(f"Scene 2 choices count: {len(sc2_choices)}")
    assert len(sc2_choices) == 2

    # Choose first option (Descend into cellar archive)
    action_2 = httpx.post(
        f"{BASE_URL}/stories/{story_id}/choice",
        headers=headers,
        json={"choice_id": sc2_choices[0]["id"]},
        timeout=10,
    )
    assert action_2.status_code == 200
    res_2 = action_2.json()
    print(f"Turn 2 Result: current_scene_id={res_2['current_scene_id']} (Expected {scene_map['cellar_archive']})")
    print(f"Turn Number: {res_2['turn_number']}, Location: '{res_2['scene_location']}', is_ending={res_2['is_ending']}")
    assert res_2["current_scene_id"] == scene_map["cellar_archive"]
    assert res_2["is_ending"] is False
    assert res_2["turn_number"] == 2

    print("\n=== Step 9: Turn 3 -> Select Choice from Scene 5 (Advance to Scene 6: The Inner Sanctum) ===")
    c5_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/scenes/{scene_map['cellar_archive']}/choices", headers=headers, timeout=10)
    sc5_choices = c5_resp.json()
    assert len(sc5_choices) == 2

    action_3 = httpx.post(
        f"{BASE_URL}/stories/{story_id}/choice",
        headers=headers,
        json={"choice_id": sc5_choices[0]["id"]},
        timeout=10,
    )
    assert action_3.status_code == 200
    res_3 = action_3.json()
    print(f"Turn 3 Result: current_scene_id={res_3['current_scene_id']} (Expected {scene_map['inner_sanctum']})")
    print(f"Turn Number: {res_3['turn_number']}, Location: '{res_3['scene_location']}', is_ending={res_3['is_ending']}")
    assert res_3["current_scene_id"] == scene_map["inner_sanctum"]
    assert res_3["is_ending"] is False
    assert res_3["turn_number"] == 3

    print("\n=== Step 10: Turn 4 -> Select Ending Choice from Scene 6 (Climax / Genuine Ending) ===")
    c6_resp = httpx.get(f"{BASE_URL}/stories/{story_id}/scenes/{scene_map['inner_sanctum']}/choices", headers=headers, timeout=10)
    sc6_choices = c6_resp.json()
    assert len(sc6_choices) == 3

    # Select Choice 1 (Unseal the sanctuary boundary -> Scene 7: The Unveiled Dawn)
    action_4 = httpx.post(
        f"{BASE_URL}/stories/{story_id}/choice",
        headers=headers,
        json={"choice_id": sc6_choices[0]["id"]},
        timeout=10,
    )
    assert action_4.status_code == 200
    res_4 = action_4.json()
    print(f"Turn 4 Result: current_scene_id={res_4['current_scene_id']} (Expected {scene_map['ending_truth']})")
    print(f"Turn Number: {res_4['turn_number']}, Location: '{res_4['scene_location']}', is_ending={res_4['is_ending']}")
    assert res_4["current_scene_id"] == scene_map["ending_truth"]
    assert res_4["is_ending"] is True
    assert res_4["turn_number"] == 4

    # Verify story status is now completed
    story_check = httpx.get(f"{BASE_URL}/stories/{story_id}", headers=headers, timeout=10).json()
    print(f"Story final status: '{story_check['status']}'")
    assert story_check["status"] == "completed"

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_gameplay_flow()
