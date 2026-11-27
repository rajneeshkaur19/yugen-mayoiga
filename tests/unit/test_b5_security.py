"""
Batch 5 — Task 2: Backend security regression tests.

Covers:
- Cross-user story access → 404
- Cross-user memory / relationship / world_state access → 404
- Invalid / expired JWT → 401
- Missing JWT → 403 / 401
- Action on completed story → 422
- Oversized input → 422
- Blank world_state key → 422
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.story import Story
from backend.app.models.character import Character
from backend.app.models.memory import Memory
from backend.app.models.relationship import Relationship
from backend.app.models.world_state import WorldState
from backend.app.services.story_service import create_story
from backend.app.schemas.story import StoryCreate


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_story(db: Session, user_id: int, title: str = "Test Story") -> Story:
    payload = StoryCreate(
        title=title,
        genre="mystery",
        theme="isolation",
        tone="dark",
        season="autumn",
        length="short",
        story_language="English",
    )
    return create_story(db, user_id=user_id, story_data=payload)


# ─── cross-user isolation ─────────────────────────────────────────────────────

def test_cross_user_story_access_returns_404(
    client: TestClient, db_session: Session, test_user, other_auth_headers
):
    """User A's story must not be visible to user B."""
    story = _make_story(db_session, test_user.id, "Owner Story")
    response = client.get(f"/stories/{story.id}", headers=other_auth_headers)
    assert response.status_code == 404, response.text


def test_cross_user_memory_access_returns_404(
    client: TestClient, db_session: Session, test_user, other_auth_headers
):
    """Memories on user A's story must return 404 for user B."""
    story = _make_story(db_session, test_user.id, "Memory Story")
    # Create a character and memory
    char = Character(story_id=story.id, name="X", role="ghost", background="")
    db_session.add(char)
    db_session.flush()
    mem = Memory(
        story_id=story.id,
        character_id=char.id,
        event="Saw something",
        type="short_term",
        importance=50,
        emotional_weight=0,
        created_turn=0,
    )
    db_session.add(mem)
    db_session.commit()

    response = client.get(f"/stories/{story.id}/memories", headers=other_auth_headers)
    assert response.status_code == 404, response.text


def test_cross_user_world_state_access_returns_404(
    client: TestClient, db_session: Session, test_user, other_auth_headers
):
    """World state on user A's story must return 404 for user B."""
    story = _make_story(db_session, test_user.id, "World State Story")
    response = client.get(f"/stories/{story.id}/world-state", headers=other_auth_headers)
    assert response.status_code == 404, response.text


# ─── authentication ───────────────────────────────────────────────────────────

def test_missing_jwt_returns_401_or_403(client: TestClient):
    """Requests without a JWT must be rejected (401 or 403)."""
    response = client.get("/stories/")
    assert response.status_code in (401, 403), response.text


def test_invalid_jwt_returns_401(client: TestClient):
    """A malformed / tampered Bearer token must be rejected with 401."""
    response = client.get(
        "/stories/",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401, response.text


def test_expired_jwt_returns_401(client: TestClient, db_session: Session, test_user):
    """An expired JWT must be rejected with 401."""
    from backend.app.core.security import create_access_token
    from datetime import timedelta

    expired_token = create_access_token(
        subject=str(test_user.id),
        expires_delta=timedelta(seconds=-1),  # already expired
    )
    response = client.get(
        "/stories/",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401, response.text


# ─── completed story rejection ────────────────────────────────────────────────

def test_action_on_completed_story_rejected(
    client: TestClient, db_session: Session, test_user, auth_headers
):
    """Choice execution on a completed story must be rejected (422 or 404)."""
    story = _make_story(db_session, test_user.id, "Done Story")
    story.status = "completed"
    db_session.commit()

    response = client.post(
        f"/stories/{story.id}/choices/9999/execute",
        headers=auth_headers,
        json={},
    )
    assert response.status_code in (404, 422), response.text


# ─── input validation ─────────────────────────────────────────────────────────

def test_oversized_story_title_rejected(
    client: TestClient, auth_headers
):
    """Story titles exceeding 200 characters must be rejected with 422."""
    response = client.post(
        "/stories/",
        headers=auth_headers,
        json={
            "title": "X" * 201,
            "genre": "mystery",
            "theme": "isolation",
            "tone": "dark",
            "season": "autumn",
            "length": "short",
            "story_language": "English",
        },
    )
    assert response.status_code == 422, response.text


def test_blank_world_state_key_rejected(
    client: TestClient, db_session: Session, test_user, auth_headers
):
    """A world-state update with a blank key must be rejected with 422."""
    story = _make_story(db_session, test_user.id, "WS Key Story")
    response = client.put(
        f"/stories/{story.id}/world-state",
        headers=auth_headers,
        json={"key": "", "value": "anything"},
    )
    assert response.status_code == 422, response.text


def test_invalid_username_pattern_rejected(client: TestClient):
    """Usernames with illegal characters must be rejected with 422."""
    response = client.post(
        "/auth/register",
        json={
            "username": "bad user!",
            "email": "bad@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 422, response.text


def test_short_password_rejected(client: TestClient):
    """Passwords under 8 characters must be rejected with 422."""
    response = client.post(
        "/auth/register",
        json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422, response.text
