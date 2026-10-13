
import pytest

from backend.app.mayoiga.choice import Choice
from backend.app.mayoiga.scene import Scene


def test_scene_stores_its_details():
    scene = Scene(
        id="scene_1",
        title="Abandoned House",
        text="Mio stands before an abandoned house.",
    )

    assert scene.id == "scene_1"
    assert scene.title == "Abandoned House"
    assert scene.text == "Mio stands before an abandoned house."
    assert scene.choices == []
    assert scene.is_ending is False


def test_scene_can_be_marked_as_ending():
    scene = Scene(
        id="scene_end",
        title="The End",
        text="The story ends here.",
        is_ending=True,
    )

    assert scene.is_ending is True


def test_add_choice_to_scene():
    scene = Scene(
        id="scene_1",
        title="Forest",
        text="A dark forest lies ahead.",
    )
    choice = Choice(
        id="choice_1",
        text="Enter the forest",
        next_scene_id="scene_2",
    )

    scene.add_choice(choice)

    assert len(scene.choices) == 1
    assert scene.choices[0] == choice


def test_duplicate_choice_id_is_rejected():
    scene = Scene(
        id="scene_1",
        title="Forest",
        text="A dark forest lies ahead.",
    )
    first_choice = Choice(
        id="choice_1",
        text="Enter the forest",
        next_scene_id="scene_2",
    )
    duplicate_choice = Choice(
        id="choice_1",
        text="Walk away",
        next_scene_id="scene_3",
    )

    scene.add_choice(first_choice)

    with pytest.raises(ValueError, match="Duplicate choice ID"):
        scene.add_choice(duplicate_choice)

    assert len(scene.choices) == 1


def test_get_choice_by_id():
    scene = Scene(
        id="scene_1",
        title="Forest",
        text="A dark forest lies ahead.",
    )
    choice = Choice(
        id="choice_1",
        text="Enter the forest",
        next_scene_id="scene_2",
    )
    scene.add_choice(choice)

    result = scene.get_choice("choice_1")

    assert result == choice


def test_get_choice_raises_error_for_unknown_id():
    scene = Scene(
        id="scene_1",
        title="Forest",
        text="A dark forest lies ahead.",
    )

    with pytest.raises(
        ValueError,
        match="Choice 'missing' not found in scene 'scene_1'",
    ):
        scene.get_choice("missing")
