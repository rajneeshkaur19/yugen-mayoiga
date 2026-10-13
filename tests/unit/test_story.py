
import pytest

from backend.app.mayoiga.choice import Choice
from backend.app.mayoiga.scene import Scene
from backend.app.mayoiga.story import Story


def create_scene(scene_id, title="Test Scene"):
    return Scene(
        id=scene_id,
        title=title,
        text=f"Text for {title}",
    )


def test_story_stores_its_details():
    story = Story(id="story_1", title="Yugen Mayoiga")

    assert story.id == "story_1"
    assert story.title == "Yugen Mayoiga"
    assert story.scenes == {}
    assert story.start_scene_id == ""


def test_add_scene_to_story():
    story = Story(id="story_1", title="Yugen Mayoiga")
    scene = create_scene("scene_1")

    story.add_scene(scene)

    assert story.scenes["scene_1"] == scene


def test_duplicate_scene_id_is_rejected():
    story = Story(id="story_1", title="Yugen Mayoiga")
    story.add_scene(create_scene("scene_1"))

    with pytest.raises(ValueError, match="Duplicate scene ID"):
        story.add_scene(create_scene("scene_1", "Another Scene"))

    assert len(story.scenes) == 1


def test_get_scene_by_id():
    story = Story(id="story_1", title="Yugen Mayoiga")
    scene = create_scene("scene_1")
    story.add_scene(scene)

    assert story.get_scene("scene_1") == scene


def test_get_missing_scene_raises_error():
    story = Story(id="story_1", title="Yugen Mayoiga")

    with pytest.raises(ValueError, match="does not exist"):
        story.get_scene("missing_scene")


def test_validate_story_with_valid_starting_scene():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="scene_1",
    )
    story.add_scene(create_scene("scene_1"))

    story.validate()


def test_validate_rejects_story_without_scenes():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="scene_1",
    )

    with pytest.raises(ValueError, match="at least one scene"):
        story.validate()


def test_validate_rejects_missing_starting_scene():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="missing_scene",
    )
    story.add_scene(create_scene("scene_1"))

    with pytest.raises(ValueError, match="starting scene must exist"):
        story.validate()


def test_validate_rejects_choice_with_missing_destination():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="scene_1",
    )
    scene = create_scene("scene_1")
    scene.add_choice(
        Choice(
            id="choice_1",
            text="Enter the forest",
            next_scene_id="missing_scene",
        )
    )
    story.add_scene(scene)

    with pytest.raises(ValueError, match="points to missing scene"):
        story.validate()


def test_validate_accepts_valid_choice_destination():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="scene_1",
    )
    scene_1 = create_scene("scene_1")
    scene_2 = create_scene("scene_2")

    scene_1.add_choice(
        Choice(
            id="choice_1",
            text="Enter the forest",
            next_scene_id="scene_2",
        )
    )

    story.add_scene(scene_1)
    story.add_scene(scene_2)

    story.validate()
