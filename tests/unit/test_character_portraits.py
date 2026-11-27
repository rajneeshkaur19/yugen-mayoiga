"""Unit and integration tests for Character Visual Profiles & Portrait Generation (Batch 1).

Tests cover:
- Character schema support for portrait_image_url, visual_description, visual_prompt_anchor
- Character model column presence and nullability
- Character prompt construction adhering to Japanese gothic / ukiyo-e aesthetic
- Character portrait generation via primary provider / fallback
- Endpoint idempotency on existing portrait
- Endpoint ownership check
- Alembic migration d4e8a1f2b3c5 upgrade and downgrade in isolated SQLite
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


def test_character_create_accepts_portrait_fields():
    from backend.app.schemas.character import CharacterCreate
    c = CharacterCreate(
        name="Chiyo",
        role="The Shrine Guardian",
        age=22,
        background="Guardian of the flooded shrine.",
        portrait_image_url="/api/generated-images/cache_chiyo.png",
        visual_description="Vermilion and white shrine robes.",
        visual_prompt_anchor="Shrine maiden holding bronze bell in cedar forest",
    )
    assert c.portrait_image_url == "/api/generated-images/cache_chiyo.png"
    assert c.visual_description == "Vermilion and white shrine robes."
    assert c.visual_prompt_anchor == "Shrine maiden holding bronze bell in cedar forest"


def test_character_create_portrait_fields_default_to_none():
    from backend.app.schemas.character import CharacterCreate
    c = CharacterCreate(
        name="Ren",
        role="The Caretaker",
    )
    assert c.portrait_image_url is None
    assert c.visual_description is None
    assert c.visual_prompt_anchor is None


def test_character_read_includes_portrait_fields():
    from backend.app.schemas.character import CharacterRead
    fields = CharacterRead.model_fields
    assert "portrait_image_url" in fields
    assert "visual_description" in fields
    assert "visual_prompt_anchor" in fields


def test_character_update_allows_portrait_fields():
    from backend.app.schemas.character import CharacterUpdate
    u = CharacterUpdate(
        portrait_image_url="/api/generated-images/cache_ren.png",
        visual_description="Haori over black kimono.",
        visual_prompt_anchor="Youth in haori holding brass lantern",
    )
    assert u.portrait_image_url == "/api/generated-images/cache_ren.png"
    assert u.visual_description == "Haori over black kimono."
    assert u.visual_prompt_anchor == "Youth in haori holding brass lantern"


# ---------------------------------------------------------------------------
# ORM Model Tests
# ---------------------------------------------------------------------------


def test_character_model_has_portrait_columns():
    from backend.app.models.character import Character
    columns = {col.name for col in Character.__table__.columns}
    assert "portrait_image_url" in columns
    assert "visual_description" in columns
    assert "visual_prompt_anchor" in columns


def test_character_model_portrait_columns_are_nullable():
    from backend.app.models.character import Character
    table = Character.__table__
    assert table.columns["portrait_image_url"].nullable is True
    assert table.columns["visual_description"].nullable is True
    assert table.columns["visual_prompt_anchor"].nullable is True


# ---------------------------------------------------------------------------
# Character Prompt Construction
# ---------------------------------------------------------------------------


def test_build_character_portrait_prompt_includes_identity():
    from backend.app.services.image_generation_service import build_character_portrait_prompt
    prompt = build_character_portrait_prompt(
        name="Chiyo",
        role="The Shrine Guardian",
        visual_description="Vermilion and white shrine robes",
        visual_prompt_anchor="Shrine maiden holding bronze bell",
    )
    assert "Chiyo" in prompt
    assert "Shrine Guardian" in prompt
    assert "Vermilion and white shrine robes" in prompt
    assert "Shrine maiden holding bronze bell" in prompt
    assert "ukiyo-e" in prompt.lower()
    assert "solo bust portrait" in prompt.lower()


# ---------------------------------------------------------------------------
# Character Portrait Generation & Fallback
# ---------------------------------------------------------------------------


def test_generate_character_portrait_with_mock_gemini(monkeypatch, tmp_path):
    from backend.app.services.image_generation_service import generate_character_portrait
    from backend.app.schemas.ai import LocationImageGenerateResponse

    valid_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
        b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
    monkeypatch.setattr(
        "backend.app.services.image_generation_service.IMAGE_STORAGE_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.services.image_generation_service._generate_with_gemini",
        lambda *args, **kwargs: (valid_png_bytes, "png", None),
    )

    result = generate_character_portrait(
        name="Aoi",
        role="The Wandering Archivist",
        visual_description="Layered indigo and cream kimono with spectacles",
    )

    assert result.success is True
    assert result.provider == "Google Gemini Image"
    assert "/api/generated-images/cache_" in result.image_url


def test_generate_character_portrait_falls_back_when_no_keys(monkeypatch, tmp_path):
    from backend.app.services.image_generation_service import generate_character_portrait

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "backend.app.services.image_generation_service.IMAGE_STORAGE_DIR",
        tmp_path,
    )

    result = generate_character_portrait(
        name="Chiyo",
        role="The Shrine Guardian",
    )

    assert result.success is True
    assert result.provider == "Curated Environmental Fallback"
    assert "shrine" in result.image_url.lower() or "mayoiga" in result.image_url.lower()


# ---------------------------------------------------------------------------
# API Endpoint Integration
# ---------------------------------------------------------------------------


def _make_mock_character(portrait_image_url: Optional[str] = None):
    m = MagicMock()
    m.id = 10
    m.story_id = 1
    m.name = "Ren"
    m.role = "The Quiet Caretaker"
    m.age = 25
    m.background = "Caretaker of the mountain estate."
    m.visual_description = "Dark haori over black kimono."
    m.visual_prompt_anchor = "Youth with lantern"
    m.portrait_image_url = portrait_image_url
    m.goals = []
    m.fears = []
    m.secrets = []
    m.traits = None
    return m


def test_generate_portrait_endpoint_is_idempotent():
    from backend.app.api.characters import generate_portrait_for_character

    mock_story = MagicMock()
    mock_char = _make_mock_character(portrait_image_url="/api/generated-images/cache_existing_ren.png")

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42

    with (
        patch("backend.app.api.characters.get_story", return_value=mock_story),
        patch("backend.app.api.characters.get_character", return_value=mock_char),
        patch("backend.app.api.characters.generate_character_portrait") as mock_gen,
    ):
        result = generate_portrait_for_character(
            story_id=1,
            character_id=10,
            db=mock_db,
            current_user=mock_user,
        )
        mock_gen.assert_not_called()
        assert result.portrait_image_url == "/api/generated-images/cache_existing_ren.png"


def test_generate_portrait_endpoint_calls_service_when_no_portrait():
    from backend.app.api.characters import generate_portrait_for_character

    mock_story = MagicMock()
    mock_char = _make_mock_character(portrait_image_url=None)

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42

    mock_response = MagicMock()
    mock_response.success = True
    mock_response.image_url = "/api/generated-images/cache_new_portrait.png"

    with (
        patch("backend.app.api.characters.get_story", return_value=mock_story),
        patch("backend.app.api.characters.get_character", return_value=mock_char),
        patch("backend.app.api.characters.generate_character_portrait", return_value=mock_response) as mock_gen,
    ):
        result = generate_portrait_for_character(
            story_id=1,
            character_id=10,
            db=mock_db,
            current_user=mock_user,
        )
        mock_gen.assert_called_once()
        assert mock_char.portrait_image_url == "/api/generated-images/cache_new_portrait.png"


def test_generate_portrait_endpoint_checks_story_ownership():
    from backend.app.api.characters import generate_portrait_for_character

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 42

    with patch("backend.app.api.characters.get_story", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            generate_portrait_for_character(
                story_id=999,
                character_id=10,
                db=mock_db,
                current_user=mock_user,
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Migration Upgrade / Downgrade Test
# ---------------------------------------------------------------------------


def test_migration_d4e8a1f2b3c5_isolated_sqlite():
    from sqlalchemy import create_engine, text, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE characters (id INTEGER PRIMARY KEY, name VARCHAR(100));"))
        conn.commit()

        spec = importlib.util.spec_from_file_location(
            "migration_d4e8a1f2b3c5",
            "alembic/versions/d4e8a1f2b3c5_add_portrait_fields_to_characters.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert mod.revision == "d4e8a1f2b3c5"
        assert mod.down_revision == "c1a9f3b8e2d4"

        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)
        mod.op = op

        # Test Upgrade
        mod.upgrade()
        conn.commit()

        insp = inspect(conn)
        cols = [c["name"] for c in insp.get_columns("characters")]
        assert "portrait_image_url" in cols
        assert "visual_description" in cols
        assert "visual_prompt_anchor" in cols

        # Test Downgrade
        mod.downgrade()
        conn.commit()

        insp = inspect(conn)
        cols_after = [c["name"] for c in insp.get_columns("characters")]
        assert "portrait_image_url" not in cols_after
        assert "visual_description" not in cols_after
        assert "visual_prompt_anchor" not in cols_after
