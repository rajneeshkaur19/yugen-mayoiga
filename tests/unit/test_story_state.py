import pytest

from backend.app.mayoiga.character import Character
from backend.app.mayoiga.choice import Choice
from backend.app.mayoiga.scene import Scene
from backend.app.mayoiga.story import Story
from backend.app.mayoiga.story_state import StoryState


def create_test_story():
    story = Story(
        id="story_1",
        title="Yugen Mayoiga",
        start_scene_id="scene_1",
    )

    scene_1 = Scene(
        id="scene_1",
        title="Forest Entrance",
        text="Mio stands at the forest entrance.",
    )
    scene_2 = Scene(
        id="scene_2",
        title="Deep Forest",
        text="Mio enters the dark forest.",
    )
    ending = Scene(
        id="ending",
        title="The End",
        text="The story ends.",
        is_ending=True,
    )

    scene_1.add_choice(
        Choice(
            id="enter",
            text="Enter the forest",
            next_scene_id="scene_2",
            emotion_deltas={"fear": 10.0},
            trait_deltas={"courage": 5.0},
        )
    )
    scene_2.add_choice(
        Choice(
            id="finish",
            text="Accept your fate",
            next_scene_id="ending",
        )
    )

    story.add_scene(scene_1)
    story.add_scene(scene_2)
    story.add_scene(ending)

    return story


def create_test_character():
    return Character(
        id="character_1",
        name="Mio",
        traits={"courage": 50.0},
        emotions={"fear": 40.0},
    )


def test_story_state_starts_at_starting_scene():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    assert state.current_scene_id == "scene_1"
    assert state.history == ["scene_1"]


def test_current_scene_returns_active_scene():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    assert state.current_scene.id == "scene_1"
    assert state.current_scene.title == "Forest Entrance"


def test_make_choice_moves_to_next_scene():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    state.make_choice("enter")

    assert state.current_scene_id == "scene_2"
    assert state.current_scene.id == "scene_2"


def test_make_choice_updates_scene_history():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    state.make_choice("enter")

    assert state.history == ["scene_1", "scene_2"]


def test_make_choice_applies_character_changes():
    character = create_test_character()
    state = StoryState(
        story=create_test_story(),
        character=character,
    )

    state.make_choice("enter")

    assert character.emotions["fear"] == 50.0
    assert character.traits["courage"] == 55.0


def test_invalid_choice_raises_error():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    with pytest.raises(ValueError, match="Choice 'missing' not found"):
        state.make_choice("missing")


def test_story_cannot_start_without_scenes():
    story = Story(id="story_1", title="Yugen Mayoiga")
    character = create_test_character()

    with pytest.raises(
        ValueError,
        match="Cannot start a story without scenes",
    ):
        StoryState(story=story, character=character)


def test_story_cannot_start_without_starting_scene():
    story = Story(id="story_1", title="Yugen Mayoiga")
    story.add_scene(
        Scene(
            id="scene_1",
            title="Forest",
            text="A dark forest.",
        )
    )

    with pytest.raises(
        ValueError,
        match="must define a starting scene",
    ):
        StoryState(story=story, character=create_test_character())


def test_nonexistent_current_scene_is_rejected():
    story = create_test_story()

    with pytest.raises(ValueError, match="does not exist"):
        StoryState(
            story=story,
            character=create_test_character(),
            current_scene_id="missing_scene",
        )


def test_choice_cannot_be_made_after_ending():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    state.make_choice("enter")
    state.make_choice("finish")

    assert state.current_scene.is_ending is True

    with pytest.raises(
        ValueError,
        match="The story has already ended",
    ):
        state.make_choice("finish")


def test_undo_restores_previous_scene():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    state.make_choice("enter")
    state.undo()

    assert state.current_scene_id == "scene_1"
    assert state.current_scene.id == "scene_1"


def test_undo_restores_character_traits_and_emotions():
    character = create_test_character()
    state = StoryState(
        story=create_test_story(),
        character=character,
    )

    state.make_choice("enter")
    state.undo()

    assert character.emotions["fear"] == 40.0
    assert character.traits["courage"] == 50.0


def test_undo_restores_scene_history():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    state.make_choice("enter")
    state.undo()

    assert state.history == ["scene_1"]


def test_multiple_undos_restore_previous_states():
    character = create_test_character()
    state = StoryState(
        story=create_test_story(),
        character=character,
    )

    state.make_choice("enter")
    state.make_choice("finish")

    state.undo()
    assert state.current_scene_id == "scene_2"
    assert character.emotions["fear"] == 50.0

    state.undo()
    assert state.current_scene_id == "scene_1"
    assert character.emotions["fear"] == 40.0
    assert character.traits["courage"] == 50.0


def test_undo_without_previous_choice_raises_error():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    with pytest.raises(ValueError, match="Nothing to undo"):
        state.undo()


def test_invalid_choice_does_not_create_undo_state():
    state = StoryState(
        story=create_test_story(),
        character=create_test_character(),
    )

    with pytest.raises(ValueError):
        state.make_choice("missing")

    with pytest.raises(ValueError, match="Nothing to undo"):
        state.undo()
