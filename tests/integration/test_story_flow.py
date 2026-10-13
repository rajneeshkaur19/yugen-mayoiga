
from backend.app.mayoiga.character import Character
from backend.app.mayoiga.choice import Choice
from backend.app.mayoiga.scene import Scene
from backend.app.mayoiga.story import Story
from backend.app.mayoiga.story_state import StoryState


def test_complete_story_flow():
    character = Character(
        id="mio",
        name="Mio",
        traits={"courage": 50.0},
        emotions={"fear": 40.0},
    )

    story = Story(
        id="yugen_1",
        title="Yugen Mayoiga",
        start_scene_id="entrance",
    )

    entrance = Scene(
        id="entrance",
        title="The Entrance",
        text="Mio finds a mysterious abandoned house.",
    )

    corridor = Scene(
        id="corridor",
        title="The Corridor",
        text="A cold wind moves through the corridor.",
    )

    ending = Scene(
        id="ending",
        title="The End",
        text="Mio discovers the truth.",
        is_ending=True,
    )

    entrance.add_choice(
        Choice(
            id="enter",
            text="Enter the house",
            next_scene_id="corridor",
            trait_deltas={"courage": 10.0},
            emotion_deltas={"fear": 5.0},
        )
    )

    corridor.add_choice(
        Choice(
            id="continue",
            text="Continue deeper",
            next_scene_id="ending",
        )
    )

    story.add_scene(entrance)
    story.add_scene(corridor)
    story.add_scene(ending)

    state = StoryState(story=story, character=character)

    assert state.current_scene_id == "entrance"
    assert state.history == ["entrance"]

    state.make_choice("enter")

    assert state.current_scene_id == "corridor"
    assert state.history == ["entrance", "corridor"]
    assert character.traits["courage"] == 60.0
    assert character.emotions["fear"] == 45.0

    state.make_choice("continue")

    assert state.current_scene_id == "ending"
    assert state.current_scene.is_ending is True
    assert state.history == ["entrance", "corridor", "ending"]
