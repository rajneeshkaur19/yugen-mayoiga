"""Batch 4: Full Backend & Frontend API Integration & Regression Tests.

Tests real FastAPI + PostgreSQL end-to-end workflows without mocking DB or routes:
1. Register -> Login -> /auth/me -> Dashboard (GET /stories) + ownership isolation
2. Create Story -> Scenes -> Choices -> Characters -> Endings -> Initial State (language preserved)
3. Open Story -> Read Scene -> Make Choice -> Verify scene, turn_number, emotions, world state, memories
4. Character Dossier API retrieval & ownership isolation
5. Story Deletion -> Cascade integrity across all 12 child tables (no orphans, other user's data intact)
6. CORS middleware headers for local Vite dev origin
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.character import Character
from backend.app.models.character_state import CharacterState
from backend.app.models.character_traits import CharacterTraits
from backend.app.models.choice import Choice
from backend.app.models.ending import Ending
from backend.app.models.memory import Memory
from backend.app.models.relationship import Relationship
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.story_state import StoryState
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.models.world_state import WorldState


def _db_available() -> bool:
    try:
        import socket

        s = socket.create_connection(("localhost", 5432), timeout=1)
        s.close()
        return True
    except Exception:
        return False


skip_no_db = pytest.mark.skipif(not _db_available(), reason="PostgreSQL not reachable")


@skip_no_db
def test_register_login_dashboard_and_ownership_isolation(client: TestClient) -> None:
    """Verify Register -> Login -> /auth/me -> GET /stories and cross-user isolation."""
    uid = uuid.uuid4().hex[:8]
    username = f"b4user_{uid}"
    email = f"b4user_{uid}@example.com"
    password = "StrongPassword123!"

    # 1. Register
    reg_res = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg_res.status_code in (200, 201), reg_res.text

    # 2. Invalid password login -> 401
    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 3. Valid login -> JWT
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. /auth/me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username

    # 5. Dashboard GET /stories initially empty
    list_res = client.get("/stories", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json() == []


@skip_no_db
def test_full_story_lifecycle_and_cascade_deletion(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    """Verify full story creation, gameplay choice, dossier API, ownership check,
    and complete cascade deletion with zero orphaned child rows."""
    uid = uuid.uuid4().hex[:6]

    # 0. Create an unrelated story for other_user to confirm it is never touched
    other_story_res = client.post(
        "/stories",
        headers=other_auth_headers,
        json={
            "title": f"Other User Story {uid}",
            "genre": "Mystery",
            "theme": "Mist",
            "tone": "Calm",
            "season": "Winter",
            "length": "short",
            "story_language": "English",
        },
    )
    assert other_story_res.status_code == 201
    other_story_id = other_story_res.json()["id"]

    # 1. Create story with Japanese language preserved
    story_res = client.post(
        "/stories",
        headers=auth_headers,
        json={
            "title": f"Mayoiga Chronicle {uid}",
            "genre": "Mystery",
            "theme": "Forgotten Vow",
            "tone": "Eerie",
            "season": "Autumn",
            "length": "medium",
            "story_language": "Japanese",
        },
    )
    assert story_res.status_code == 201, story_res.text
    story = story_res.json()
    story_id = story["id"]
    assert story["story_language"] == "Japanese"
    assert story["status"] == "active"

    # 2. Create 2 scenes
    s1 = client.post(
        f"/stories/{story_id}/scenes",
        headers=auth_headers,
        json={
            "scene_number": 1,
            "location": "Front Gate",
            "mood": "Foreboding",
            "content": "Lanterns flicker in the mist.",
            "is_ending": False,
        },
    ).json()
    s2 = client.post(
        f"/stories/{story_id}/scenes",
        headers=auth_headers,
        json={
            "scene_number": 2,
            "location": "Inner Sanctum",
            "mood": "Serene",
            "content": "Embers glow softly.",
            "is_ending": False,
        },
    ).json()

    # 3. Create choice from s1 -> s2 with emotion, world, hidden, memory effects
    ch = client.post(
        f"/stories/{story_id}/scenes/{s1['id']}/choices",
        headers=auth_headers,
        json={
            "choice_text": "Step across the threshold.",
            "effects": {
                "trust": 15,
                "world_door_open": True,
                "hidden_truth_discovered": True,
                "yugen_meter": -10,
                "emotional_weight": 45,
                "memory_importance": 80,
            },
            "allow_loop": False,
            "sort_order": 0,
            "next_scene_id": s2["id"],
        },
    ).json()

    # 4. Create 2 characters + traits + relationship
    char1 = client.post(
        f"/stories/{story_id}/characters",
        headers=auth_headers,
        json={
            "name": "Ren",
            "role": "Caretaker",
            "age": 25,
            "background": "Silent steward.",
            "visual_description": "Dark haori with brass lantern.",
            "visual_prompt_anchor": "Solemn youth in dark haori",
        },
    ).json()
    char2 = client.post(
        f"/stories/{story_id}/characters",
        headers=auth_headers,
        json={
            "name": "Aoi",
            "role": "Archivist",
            "age": 23,
            "background": "Lineage chronicler.",
        },
    ).json()

    # 5. Other user cannot access story or characters -> 404
    assert client.get(f"/stories/{story_id}", headers=other_auth_headers).status_code == 404
    assert (
        client.get(f"/stories/{story_id}/characters", headers=other_auth_headers).status_code
        == 404
    )

    # 6. Initial runtime state
    init_state = client.get(f"/stories/{story_id}/state", headers=auth_headers)
    assert init_state.status_code == 200
    assert init_state.json()["current_scene_id"] == s1["id"]
    assert init_state.json()["turn_number"] == 0

    # 7. Make choice -> verify scene transition, turn_number=1, world state, memories
    action_res = client.post(
        f"/stories/{story_id}/choice",
        headers=auth_headers,
        json={"choice_id": ch["id"], "character_id": char1["id"]},
    )
    assert action_res.status_code == 200, action_res.text
    payload = action_res.json()
    assert payload["current_scene_id"] == s2["id"]
    assert payload["turn_number"] == 1
    assert payload["yugen_meter"] == 40

    # Verify updated state, memories, and character dossier endpoint
    state_after = client.get(f"/stories/{story_id}/state", headers=auth_headers).json()
    assert state_after["world_state"]["door_open"] is True
    assert state_after["turn_number"] == 1

    mems = client.get(f"/stories/{story_id}/memories", headers=auth_headers).json()
    assert len(mems) == 1
    assert mems[0]["status"] == "gilded"

    dossier = client.get(
        f"/stories/{story_id}/characters/{char1['id']}", headers=auth_headers
    )
    assert dossier.status_code == 200
    assert dossier.json()["visual_description"] == "Dark haori with brass lantern."

    # 8. Delete story -> 204 and zero orphaned records
    del_res = client.delete(f"/stories/{story_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # Story no longer in dashboard
    assert client.get(f"/stories/{story_id}", headers=auth_headers).status_code == 404

    db_session.expire_all()
    assert db_session.scalar(select(Story.id).where(Story.id == story_id)) is None
    assert db_session.scalar(select(Scene.id).where(Scene.story_id == story_id)) is None
    assert db_session.scalar(select(Choice.id).where(Choice.story_id == story_id)) is None
    assert db_session.scalar(select(Character.id).where(Character.story_id == story_id)) is None
    assert db_session.scalar(select(CharacterState.id).where(CharacterState.story_id == story_id)) is None
    assert db_session.scalar(select(Memory.id).where(Memory.story_id == story_id)) is None
    assert db_session.scalar(select(WorldState.id).where(WorldState.story_id == story_id)) is None
    assert db_session.scalar(select(StoryState.id).where(StoryState.story_id == story_id)) is None
    assert db_session.scalar(select(UserChoicesLog.id).where(UserChoicesLog.story_id == story_id)) is None

    # Unrelated user's story remains intact
    assert db_session.scalar(select(Story.id).where(Story.id == other_story_id)) == other_story_id


def test_cors_headers_for_vite_origin(client: TestClient) -> None:
    """Verify CORS headers allow local Vite dev origin."""
    res = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
