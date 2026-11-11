"""Pytest fixtures for Yūgen Mayoiga backend and integration tests."""

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token, get_password_hash
from backend.app.database.session import SessionLocal
from backend.app.main import app
from backend.app.models.character import Character
from backend.app.models.character_traits import CharacterTraits
from backend.app.models.choice import Choice
from backend.app.models.ending import Ending
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.user import User


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a real PostgreSQL database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Create a temporary test user in PostgreSQL."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"tester_{uid}",
        email=f"tester_{uid}@example.com",
        password_hash=get_password_hash("test_password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def other_user(db_session: Session) -> User:
    """Create a second distinct user to test authorization/ownership isolation."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"other_{uid}",
        email=f"other_{uid}@example.com",
        password_hash=get_password_hash("other_password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict[str, str]:
    """Return JWT Bearer authorization headers for test_user."""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def other_auth_headers(other_user: User) -> dict[str, str]:
    """Return JWT Bearer authorization headers for other_user."""
    token = create_access_token(subject=str(other_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def setup_story(db_session: Session, test_user: User) -> dict:
    """Create a complete test story with 2 scenes, a choice, a character, and an ending."""
    uid = uuid.uuid4().hex[:6]
    story = Story(
        user_id=test_user.id,
        title=f"Test Tale {uid}",
        genre="Mystery",
        theme="Isolation",
        tone="Eerie",
        season="Autumn",
        length="short",
        status="active",
    )
    db_session.add(story)
    db_session.flush()

    # Scenes
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

    # Choice from scene 1 -> scene 2
    choice = Choice(
        story_id=story.id,
        scene_id=scene1.id,
        choice_text="Step across the threshold into the dark corridor.",
        effects={
            "fear": 15,
            "world_door": "unlocked",
            "hidden_truth_discovered": True,
            "yugen_meter": -10,
        },
        next_scene_id=scene2.id,
    )
    db_session.add(choice)

    # Character
    char = Character(
        story_id=story.id,
        name=f"Aki_{uid}",
        role="Guide",
        age=21,
        background="A villager who knows the legends of Mayoiga.",
    )
    db_session.add(char)
    db_session.flush()

    # Traits
    traits = CharacterTraits(
        character_id=char.id,
        openness=70,
        conscientiousness=60,
        extraversion=40,
        agreeableness=65,
        neuroticism=55,
    )
    db_session.add(traits)

    # Ending definition
    ending = Ending(
        story_id=story.id,
        name=f"Dawn of Truth {uid}",
        conditions={"truth_discovered": True},
        seal_text="TRUTH_SEAL",
    )
    db_session.add(ending)
    db_session.commit()

    return {
        "story": story,
        "scene1": scene1,
        "scene2": scene2,
        "scene_ending": scene_ending,
        "choice": choice,
        "character": char,
        "ending": ending,
    }
