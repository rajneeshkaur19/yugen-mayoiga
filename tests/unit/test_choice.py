
from backend.app.mayoiga.character import Character
from backend.app.mayoiga.choice import Choice


def test_choice_stores_its_details():
    choice = Choice(
        id="choice_1",
        text="Enter the forest",
        next_scene_id="scene_2",
    )

    assert choice.id == "choice_1"
    assert choice.text == "Enter the forest"
    assert choice.next_scene_id == "scene_2"


def test_choice_applies_emotion_changes():
    character = Character(
        id="c1",
        name="Mio",
        emotions={"fear": 40.0},
    )
    choice = Choice(
        id="choice_1",
        text="Face the darkness",
        next_scene_id="scene_2",
        emotion_deltas={"fear": 15.0},
    )

    choice.apply_to(character)

    assert character.emotions["fear"] == 55.0


def test_choice_applies_trait_changes():
    character = Character(
        id="c1",
        name="Mio",
        traits={"courage": 50.0},
    )
    choice = Choice(
        id="choice_1",
        text="Stand your ground",
        next_scene_id="scene_2",
        trait_deltas={"courage": 10.0},
    )

    choice.apply_to(character)

    assert character.traits["courage"] == 60.0


def test_choice_applies_emotion_and_trait_changes_together():
    character = Character(
        id="c1",
        name="Mio",
        traits={"courage": 50.0},
        emotions={"fear": 40.0},
    )
    choice = Choice(
        id="choice_1",
        text="Protect your friend",
        next_scene_id="scene_2",
        emotion_deltas={"fear": -10.0},
        trait_deltas={"courage": 15.0},
    )

    choice.apply_to(character)

    assert character.emotions["fear"] == 30.0
    assert character.traits["courage"] == 65.0


def test_choice_respects_character_value_boundaries():
    character = Character(
        id="c1",
        name="Mio",
        traits={"courage": 95.0},
        emotions={"fear": 5.0},
    )
    choice = Choice(
        id="choice_1",
        text="Make a desperate decision",
        next_scene_id="scene_2",
        emotion_deltas={"fear": -20.0},
        trait_deltas={"courage": 20.0},
    )

    choice.apply_to(character)

    assert character.emotions["fear"] == 0.0
    assert character.traits["courage"] == 100.0
