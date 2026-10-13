
from backend.app.mayoiga import Character, Choice, Scene, Story, StoryState


def build_story():
    character = Character(
        id="player",
        name="The Wanderer",
        traits={"courage": 50, "honesty": 50},
        emotions={"fear": 50, "trust": 50},
    )

    shrine = Scene(
        id="shrine",
        title="The Abandoned Shrine",
        text=(
            "Rain falls over an abandoned shrine. "
            "A pale lantern flickers between the trees."
        ),
        choices=[
            Choice(
                id="follow",
                text="Follow the lantern into the forest",
                next_scene_id="forest",
                emotion_deltas={"fear": 10, "trust": 5},
                trait_deltas={"courage": 5},
            ),
            Choice(
                id="leave",
                text="Leave the shrine and return home",
                next_scene_id="home",
                emotion_deltas={"fear": -10},
            ),
        ],
    )

    forest = Scene(
        id="forest",
        title="The Whispering Forest",
        text=(
            "A forgotten voice calls your name. "
            "Something in the mist seems to remember you."
        ),
        choices=[
            Choice(
                id="answer",
                text="Answer the mysterious voice honestly",
                next_scene_id="truth",
                emotion_deltas={"trust": 15, "fear": -5},
                trait_deltas={"honesty": 10},
            ),
            Choice(
                id="hide",
                text="Stay silent and hide in the mist",
                next_scene_id="silence",
                emotion_deltas={"fear": 10},
                trait_deltas={"courage": -5},
            ),
        ],
    )

    endings = [
        Scene(
            id="home",
            title="The Familiar Road",
            text="You return home, but the lantern follows you in your dreams.",
            is_ending=True,
        ),
        Scene(
            id="truth",
            title="The Forgotten Memory",
            text="The voice reveals a memory you thought you had lost.",
            is_ending=True,
        ),
        Scene(
            id="silence",
            title="The Endless Mist",
            text="The forest grows silent. You are no longer certain of the way out.",
            is_ending=True,
        ),
    ]

    story = Story(
        id="yugen-demo",
        title="The Lantern in the Mist",
        start_scene_id="shrine",
    )

    for scene in [shrine, forest, *endings]:
        story.add_scene(scene)

    story.validate()
    state = StoryState(story=story, character=character)

    return state


def play():
    state = build_story()

    print(f"\n=== {state.story.title} ===")
    print(f"Playing as: {state.character.name}\n")

    while True:
        scene = state.current_scene

        print(f"\n--- {scene.title} ---")
        print(scene.text)

        if scene.is_ending:
            print("\n=== STORY ENDED ===")
            print(f"Path taken: {' -> '.join(state.history)}")
            print(f"Fear: {state.character.emotions.get('fear', 50)}")
            print(f"Trust: {state.character.emotions.get('trust', 50)}")
            print(f"Courage: {state.character.traits.get('courage', 50)}")
            print(f"Honesty: {state.character.traits.get('honesty', 50)}")
            break

        print("\nChoices:")
        for index, choice in enumerate(scene.choices, start=1):
            print(f"{index}. {choice.text}")

        try:
            selected = int(input("\nChoose an option: "))
            if not 1 <= selected <= len(scene.choices):
                print("Invalid option. Try again.")
                continue

            choice = scene.choices[selected - 1]
            state.make_choice(choice.id)

        except ValueError as error:
            # Invalid numeric input is handled separately from engine errors.
            if str(error).startswith("invalid literal"):
                print("Please enter a number.")
            else:
                raise


if __name__ == "__main__":
    play()
