"""Unit tests for Phase 2 — Story and Scene image URL integration.

Tests cover:
- Story creation with cover_image_url persisted
- Story retrieval returns cover_image_url
- Story update can set/clear cover_image_url
- Scene creation with scene_image_url persisted
- Scene retrieval returns scene_image_url
- Existing stories without images remain valid (None)
- Scene image URL can be updated via patch
- Alembic migration file is syntactically correct
- Scene prompt builder returns correct components
- Scene image generation endpoint: idempotent on existing image
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Schema Tests (no DB needed)
# ---------------------------------------------------------------------------


def test_story_create_accepts_cover_image_url():
    from backend.app.schemas.story import StoryCreate
    s = StoryCreate(
        title="Fogbound Estate",
        genre="Mystery",
        theme="A silent manor",
        tone="Melancholic",
        season="Autumn",
        length="short",
        story_language="English",
        cover_image_url="/api/generated-images/cache_abc123.png",
    )
    assert s.cover_image_url == "/api/generated-images/cache_abc123.png"


def test_story_create_cover_image_url_defaults_to_none():
    from backend.app.schemas.story import StoryCreate
    s = StoryCreate(
        title="Fog",
        genre="Mystery",
        theme="A silent manor",
        tone="Quiet",
        season="Winter",
        length="short",
    )
    assert s.cover_image_url is None


def test_story_read_includes_cover_image_url_field():
    from backend.app.schemas.story import StoryRead
    fields = StoryRead.model_fields
    assert "cover_image_url" in fields


def test_story_update_allows_cover_image_url():
    from backend.app.schemas.story import StoryUpdate
    u = StoryUpdate(cover_image_url="/api/generated-images/cache_xyz.jpeg")
    assert u.cover_image_url == "/api/generated-images/cache_xyz.jpeg"


def test_story_update_cover_image_url_nullable():
    from backend.app.schemas.story import StoryUpdate
    u = StoryUpdate(cover_image_url=None)
    assert u.cover_image_url is None


def test_scene_create_accepts_scene_image_url():
    from backend.app.schemas.scene import SceneCreate
    s = SceneCreate(
        scene_number=1,
        content="Mist drifts through the torii gate.",
        location="The Shrine Path",
        mood="Eerie",
        scene_image_url="/api/generated-images/cache_scene1.png",
    )
    assert s.scene_image_url == "/api/generated-images/cache_scene1.png"


def test_scene_create_scene_image_url_defaults_to_none():
    from backend.app.schemas.scene import SceneCreate
    s = SceneCreate(
        scene_number=1,
        content="Mist.",
        location="Shrine",
        mood="Quiet",
    )
    assert s.scene_image_url is None


def test_scene_read_includes_scene_image_url_field():
    from backend.app.schemas.scene import SceneRead
    fields = SceneRead.model_fields
    assert "scene_image_url" in fields


def test_scene_update_allows_scene_image_url():
    from backend.app.schemas.scene import SceneUpdate
    u = SceneUpdate(scene_image_url="/api/generated-images/cache_s2.jpeg")
    assert u.scene_image_url == "/api/generated-images/cache_s2.jpeg"


# ---------------------------------------------------------------------------
# ORM Model Tests (no DB, check column presence via SQLAlchemy mapper)
# ---------------------------------------------------------------------------


def test_story_model_has_cover_image_url_column():
    from backend.app.models.story import Story
    columns = {c.name for c in Story.__table__.columns}
    assert "cover_image_url" in columns


def test_story_model_cover_image_url_is_nullable():
    from backend.app.models.story import Story
    col = Story.__table__.columns["cover_image_url"]
    assert col.nullable is True


def test_scene_model_has_scene_image_url_column():
    from backend.app.models.scene import Scene
    columns = {c.name for c in Scene.__table__.columns}
    assert "scene_image_url" in columns


def test_scene_model_scene_image_url_is_nullable():
    from backend.app.models.scene import Scene
    col = Scene.__table__.columns["scene_image_url"]
    assert col.nullable is True


# ---------------------------------------------------------------------------
# Pydantic Read Schema Tests — real datetimes, no ORM objects
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)


def test_stories_without_cover_image_url_return_none():
    """Existing stories without images must keep returning None."""
    from backend.app.schemas.story import StoryRead
    story_data = {
        "id": 1,
        "user_id": 1,
        "title": "Old Chronicle",
        "genre": "Mystery",
        "theme": "Theme",
        "tone": "Quiet",
        "season": "Winter",
        "length": "short",
        "story_language": "English",
        "cover_image_url": None,
        "status": "active",
        "created_at": _NOW,
    }
    result = StoryRead(**story_data)
    assert result.cover_image_url is None


def test_stories_with_cover_image_url_round_trip():
    """Stories with an image URL round-trip correctly through StoryRead."""
    from backend.app.schemas.story import StoryRead
    url = "/api/generated-images/cache_abc123.png"
    story_data = {
        "id": 2,
        "user_id": 1,
        "title": "AI-covered Chronicle",
        "genre": "Mystery",
        "theme": "Theme",
        "tone": "Quiet",
        "season": "Autumn",
        "length": "medium",
        "story_language": "English",
        "cover_image_url": url,
        "status": "active",
        "created_at": _NOW,
    }
    result = StoryRead(**story_data)
    assert result.cover_image_url == url


def test_scenes_without_scene_image_url_return_none():
    """Scenes without images must keep returning None."""
    from backend.app.schemas.scene import SceneRead
    scene_data = {
        "id": 1,
        "story_id": 1,
        "scene_number": 1,
        "content": "Mist.",
        "location": "Shrine",
        "mood": "Eerie",
        "haiku": None,
        "scene_image_url": None,
        "is_ending": False,
        "created_at": _NOW,
    }
    result = SceneRead(**scene_data)
    assert result.scene_image_url is None


def test_scenes_with_scene_image_url_round_trip():
    """Scenes with a scene image URL round-trip correctly through SceneRead."""
    from backend.app.schemas.scene import SceneRead
    url = "/api/generated-images/cache_scene1.png"
    scene_data = {
        "id": 2,
        "story_id": 1,
        "scene_number": 2,
        "content": "Stone steps descend into mist.",
        "location": "The Shrine Path",
        "mood": "Eerie",
        "haiku": None,
        "scene_image_url": url,
        "is_ending": False,
        "created_at": _NOW,
    }
    result = SceneRead(**scene_data)
    assert result.scene_image_url == url


# ---------------------------------------------------------------------------
# Service Layer Tests (mocked DB session, MagicMock ORM objects)
# ---------------------------------------------------------------------------


def _make_mock_story(cover_image_url: Optional[str] = None):
    """Return a MagicMock that quacks like a Story ORM instance."""
    m = MagicMock()
    m.id = 1
    m.user_id = 42
    m.title = "Test Chronicle"
    m.genre = "Mystery"
    m.theme = "A silent manor"
    m.tone = "Melancholic"
    m.season = "Autumn"
    m.length = "short"
    m.story_language = "English"
    m.status = "active"
    m.cover_image_url = cover_image_url
    m.created_at = _NOW
    return m


def _make_mock_scene(scene_image_url: Optional[str] = None):
    """Return a MagicMock that quacks like a Scene ORM instance."""
    m = MagicMock()
    m.id = 1
    m.story_id = 1
    m.scene_number = 1
    m.content = "Stone steps descend into mist."
    m.location = "The Shrine Path"
    m.mood = "Eerie"
    m.haiku = None
    m.scene_image_url = scene_image_url
    m.is_ending = False
    m.created_at = _NOW
    return m


def test_create_story_passes_cover_image_url_to_orm():
    """create_story uses model_dump() which now includes cover_image_url."""
    from backend.app.schemas.story import StoryCreate
    from backend.app.services.story_service import create_story

    mock_story = _make_mock_story(cover_image_url="/api/generated-images/cache_foo.png")
    db = MagicMock()
    db.refresh.side_effect = lambda obj: None

    with patch("backend.app.services.story_service.Story", return_value=mock_story) as MockStory:
        create_story(
            db,
            user_id=42,
            story_data=StoryCreate(
                title="Fog",
                genre="Mystery",
                theme="Silent manor",
                tone="Quiet",
                season="Winter",
                length="short",
                cover_image_url="/api/generated-images/cache_foo.png",
            ),
        )
        call_kwargs = MockStory.call_args.kwargs
        assert call_kwargs.get("cover_image_url") == "/api/generated-images/cache_foo.png"


def test_scene_create_service_passes_scene_image_url():
    """create_scene explicitly passes scene_image_url from SceneCreate."""
    from backend.app.schemas.scene import SceneCreate
    from backend.app.services.scene_service import create_scene

    mock_scene = _make_mock_scene(scene_image_url="/api/generated-images/cache_s1.png")
    db = MagicMock()
    db.refresh.side_effect = lambda obj: None

    with patch("backend.app.services.scene_service.Scene", return_value=mock_scene) as MockScene:
        create_scene(
            db,
            story_id=1,
            data=SceneCreate(
                scene_number=1,
                content="Mist.",
                location="Shrine",
                mood="Eerie",
                scene_image_url="/api/generated-images/cache_s1.png",
            ),
        )
        call_kwargs = MockScene.call_args.kwargs
        assert call_kwargs.get("scene_image_url") == "/api/generated-images/cache_s1.png"


# ---------------------------------------------------------------------------
# Scene Prompt Builder Tests
# ---------------------------------------------------------------------------


def test_build_scene_prompt_contains_location():
    from backend.app.services.image_generation_service import build_scene_prompt
    prompt = build_scene_prompt(location="The Shrine Path", mood="Eerie")
    assert "Shrine Path" in prompt


def test_build_scene_prompt_contains_mood():
    from backend.app.services.image_generation_service import build_scene_prompt
    prompt = build_scene_prompt(location="Anywhere", mood="Melancholic")
    assert "Melancholic" in prompt


def test_build_scene_prompt_contains_season():
    from backend.app.services.image_generation_service import build_scene_prompt
    prompt = build_scene_prompt(location="Anywhere", season="Autumn")
    assert "Autumn" in prompt


def test_build_scene_prompt_contains_style_anchors():
    from backend.app.services.image_generation_service import build_scene_prompt
    prompt = build_scene_prompt(location="Anywhere")
    assert "NO characters" in prompt or "NO people" in prompt


def test_build_scene_prompt_truncates_long_content():
    from backend.app.services.image_generation_service import build_scene_prompt
    long_content = "word " * 500
    prompt = build_scene_prompt(location="Anywhere", content=long_content)
    assert len(prompt) < 2000


# ---------------------------------------------------------------------------
# Scene Image Generation — Idempotency Test
# ---------------------------------------------------------------------------


def test_generate_image_for_scene_is_idempotent_when_already_set():
    """API endpoint should return the existing scene without calling providers if image already exists."""
    from backend.app.api.scenes import generate_image_for_scene

    mock_story = _make_mock_story()
    mock_scene = _make_mock_scene(scene_image_url="/api/generated-images/cache_existing.png")

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42

    with (
        patch("backend.app.api.scenes.get_story", return_value=mock_story),
        patch("backend.app.api.scenes.get_scene", return_value=mock_scene),
        patch("backend.app.api.scenes.generate_scene_image") as mock_gen,
    ):
        result = generate_image_for_scene(
            story_id=1,
            scene_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        mock_gen.assert_not_called()
        assert result.scene_image_url == "/api/generated-images/cache_existing.png"


def test_generate_image_for_scene_calls_provider_when_no_image():
    """API endpoint calls generate_scene_image when scene has no image yet."""
    from backend.app.api.scenes import generate_image_for_scene
    from backend.app.schemas.ai import LocationImageGenerateResponse

    mock_story = _make_mock_story()
    mock_scene = _make_mock_scene(scene_image_url=None)  # No existing image

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42

    mock_response = MagicMock()
    mock_response.success = True
    mock_response.image_url = "/api/generated-images/cache_new.png"

    with (
        patch("backend.app.api.scenes.get_story", return_value=mock_story),
        patch("backend.app.api.scenes.get_scene", return_value=mock_scene),
        patch("backend.app.api.scenes.generate_scene_image", return_value=mock_response) as mock_gen,
    ):
        generate_image_for_scene(
            story_id=1,
            scene_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Alembic Migration File Structural Test
# ---------------------------------------------------------------------------


def test_alembic_migration_image_urls_is_importable():
    """The new migration file must be importable with correct revision metadata."""
    spec_path = pathlib.Path(
        "alembic/versions/c1a9f3b8e2d4_add_image_urls_to_stories_and_scenes.py"
    )
    assert spec_path.exists(), "Migration file must exist"
    spec = importlib.util.spec_from_file_location("migration_c1a9f3b8e2d4", spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "c1a9f3b8e2d4"
    assert module.down_revision == "084b1ba43ffb"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_migration_upgrade_and_downgrade_isolated_sqlite():
    """Verify upgrade() and downgrade() execute cleanly on an isolated test database."""
    from sqlalchemy import create_engine, text, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE stories (id INTEGER PRIMARY KEY, title VARCHAR(200));"))
        conn.execute(text("CREATE TABLE scenes (id INTEGER PRIMARY KEY, content TEXT);"))
        conn.commit()

        spec = importlib.util.spec_from_file_location(
            "migration_c1a9f3b8e2d4",
            "alembic/versions/c1a9f3b8e2d4_add_image_urls_to_stories_and_scenes.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        mod.op = op

        # Test Upgrade
        mod.upgrade()
        conn.commit()

        insp = inspect(conn)
        assert "cover_image_url" in [c["name"] for c in insp.get_columns("stories")]
        assert "scene_image_url" in [c["name"] for c in insp.get_columns("scenes")]

        # Test Downgrade
        mod.downgrade()
        conn.commit()

        insp = inspect(conn)
        assert "cover_image_url" not in [c["name"] for c in insp.get_columns("stories")]
        assert "scene_image_url" not in [c["name"] for c in insp.get_columns("scenes")]

