from backend.app.mayoiga.character import Character
def test_character_initial_values():
    character = Character(
        id="c1",
        name="Mio",
        traits={"courage":60.0},
        emotions={"fear":30.0},
    )
    assert character.traits["courage"] == 60.0
    assert character.emotions["fear"] == 30.0

def test_trait_increases_correctly():
    character = Character(
        id="c1", name="Mio", traits={"courage":60.0}
    )
    character.update_trait("courage",10.0)
    assert character.traits["courage"] == 70.0

def test_trait_cannot_exceed_100():
    character = Character(
        id="c1", name="Mio", traits={"courage":95.0}
    )

    character.update_trait("courage",10.0)
    assert character.traits["courage"] == 100.0

def test_trait_cannot_fall_below_zero():
    character = Character(
        id="c1",name="Mio", traits={"courage":5.0}
    )
    character.update_trait("courage",-10.0)
    assert character.traits["courage"] == 0.0 

def test_emotion_cannot_exceed_100():
    character = Character(
        id="c1",name="Mio",emotions={"fear":95.0}
    )
    character.update_emotion("fear",10.0)
    assert character.emotions["fear"] == 100.0

def test_missing_trait_uses_default_value():
    character = Character(id="c1",name="Mio",)
    character.update_trait("courage",10.0)
    assert character.traits["courage"] == 60.0
