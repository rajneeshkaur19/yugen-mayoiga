import pytest
from fastapi.testclient import TestClient


def test_unauthenticated_requests_rejected(client: TestClient, setup_story: dict):
    story_id = setup_story["story"].id

    r1 = client.get(f"/stories/{story_id}/state")
    assert r1.status_code == 401

    r2 = client.post(f"/stories/{story_id}/choice", json={"choice_id": 1})
    assert r2.status_code == 401

    r3 = client.get(f"/stories/{story_id}/relationships")
    assert r3.status_code == 401

    r4 = client.get(f"/stories/{story_id}/world-state")
    assert r4.status_code == 401

    r5 = client.get("/users/me/endings")
    assert r5.status_code == 401


def test_story_ownership_enforced(
    client: TestClient,
    setup_story: dict,
    other_auth_headers: dict,
):
    story_id = setup_story["story"].id

    # User B attempting to access User A's story state
    resp = client.get(
        f"/stories/{story_id}/state",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Story not found"

    # User B attempting to act on User A's story
    resp2 = client.post(
        f"/stories/{story_id}/choice",
        json={"choice_id": setup_story["choice"].id},
        headers=other_auth_headers,
    )
    assert resp2.status_code == 404


def test_api_get_state_and_yugen_meter(
    client: TestClient,
    setup_story: dict,
    auth_headers: dict,
):
    story_id = setup_story["story"].id

    # GET state
    res = client.get(f"/stories/{story_id}/state", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["story_id"] == story_id
    assert "yugen_meter" in data
    assert "characters" in data
    assert "world_state" in data

    # GET yugen-meter
    res_meter = client.get(f"/stories/{story_id}/yugen-meter", headers=auth_headers)
    assert res_meter.status_code == 200
    meter_data = res_meter.json()
    assert meter_data["story_id"] == story_id
    assert "yugen_meter" in meter_data
    assert "mystery_description" in meter_data


def test_api_submit_choice_action(
    client: TestClient,
    setup_story: dict,
    auth_headers: dict,
):
    story_id = setup_story["story"].id
    choice_id = setup_story["choice"].id

    payload = {"choice_id": choice_id}
    res = client.post(
        f"/stories/{story_id}/choice",
        json=payload,
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["story_id"] == story_id
    assert data["turn_number"] == 1
    assert data["scene_location"] == "Irori Hearth"
    assert data["yugen_meter"] == 40
    assert len(data["achieved_endings"]) >= 1


def test_api_world_state_endpoints(
    client: TestClient,
    setup_story: dict,
    auth_headers: dict,
):
    story_id = setup_story["story"].id

    # PUT world var
    res_put = client.put(
        f"/stories/{story_id}/world-state",
        json={"key": "hearth_fire", "value": "glowing"},
        headers=auth_headers,
    )
    assert res_put.status_code == 200
    assert res_put.json()["hearth_fire"] == "glowing"

    # GET world state
    res_get = client.get(f"/stories/{story_id}/world-state", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["hearth_fire"] == "glowing"


def test_api_relationships_endpoints(
    client: TestClient,
    setup_story: dict,
    auth_headers: dict,
    db_session,
):
    story_id = setup_story["story"].id
    char1_id = setup_story["character"].id

    # Add second character
    from backend.app.models.character import Character
    char2 = Character(story_id=story_id, name="TestRen", role="Friend")
    db_session.add(char2)
    db_session.commit()
    db_session.refresh(char2)

    # POST relationship
    payload = {
        "from_character": char1_id,
        "to_character": char2.id,
        "trust": 65,
        "suspicion": 20,
    }
    res_post = client.post(
        f"/stories/{story_id}/relationships",
        json=payload,
        headers=auth_headers,
    )
    assert res_post.status_code == 201
    assert res_post.json()["trust"] == 65

    # GET relationships
    res_get = client.get(f"/stories/{story_id}/relationships", headers=auth_headers)
    assert res_get.status_code == 200
    assert len(res_get.json()) >= 1


def test_api_endings_and_gallery_endpoints(
    client: TestClient,
    setup_story: dict,
    auth_headers: dict,
):
    story_id = setup_story["story"].id

    # GET endings for story
    res_list = client.get(f"/stories/{story_id}/endings", headers=auth_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # POST new ending definition
    payload = {
        "name": "Secret Garden Path",
        "conditions": {"secret_key": True},
        "seal_text": "GARDEN_SECRET",
    }
    res_create = client.post(
        f"/stories/{story_id}/endings",
        json=payload,
        headers=auth_headers,
    )
    assert res_create.status_code == 201
    assert res_create.json()["name"] == "Secret Garden Path"

    # GET user's unlocked endings gallery
    res_gallery = client.get("/users/me/endings", headers=auth_headers)
    assert res_gallery.status_code == 200
    assert isinstance(res_gallery.json(), list)


def test_api_e2e_register_login_story_action(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@example.com"
    pwd = "SecurePassword123!"

    # 1. Register
    reg_resp = client.post("/auth/register", json={
        "username": f"player_{uid}",
        "email": email,
        "password": pwd,
    })
    assert reg_resp.status_code == 201

    # 2. Login
    login_resp = client.post("/auth/login", json={
        "email": email,
        "password": pwd,
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Story
    story_resp = client.post("/stories", json={
        "title": "Night in Mayoiga",
        "genre": "Folklore",
        "theme": "Supernatural",
        "tone": "Mysterious",
        "season": "Spring",
        "length": "short",
    }, headers=headers)
    assert story_resp.status_code == 201
    s_id = story_resp.json()["id"]

    # 4. Create Scenes
    sc1 = client.post(f"/stories/{s_id}/scenes", json={
        "scene_number": 1,
        "content": "The grand gate stands ajar.",
        "location": "Torii Gate",
        "mood": "Mystic",
        "is_ending": False,
    }, headers=headers).json()

    sc2 = client.post(f"/stories/{s_id}/scenes", json={
        "scene_number": 2,
        "content": "A hidden courtyard bathed in moonlight.",
        "location": "Moonlit Courtyard",
        "mood": "Calm",
        "is_ending": False,
    }, headers=headers).json()

    # 5. Create Choice
    ch = client.post(f"/stories/{s_id}/scenes/{sc1['id']}/choices", json={
        "choice_text": "Pass through the Torii gate.",
        "effects": {"trust": 15, "world_torii": "passed", "yugen_meter": -5},
        "next_scene_id": sc2["id"],
    }, headers=headers).json()

    # 6. Create Character
    char = client.post(f"/stories/{s_id}/characters", json={
        "name": "Kiyomi",
        "role": "Traveler",
    }, headers=headers).json()

    # 7. Action execution via API
    act_resp = client.post(f"/stories/{s_id}/choice", json={
        "choice_id": ch["id"],
        "character_id": char["id"],
    }, headers=headers)
    assert act_resp.status_code == 200
    data = act_resp.json()
    assert data["turn_number"] == 1
    assert data["current_scene_id"] == sc2["id"]
    assert data["scene_location"] == "Moonlit Courtyard"
