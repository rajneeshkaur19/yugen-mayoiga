import pytest
from algorithms.dialogue_tree import DialogueTree, DialogueNode
from algorithms.state_store import StateStore


def test_dialogue_tree_creation_and_root():
    tree = DialogueTree()
    root = DialogueNode(
        node_id="D1",
        speaker="Mayu",
        text="Who enters the lost house?",
        character_id=1,
    )
    tree.add_node(root)

    assert tree.get_root() == root
    assert tree.get_node("D1") == root


def test_dialogue_tree_branching_and_traversal():
    tree = DialogueTree()
    root = DialogueNode(node_id="D1", speaker="Mayu", text="Who are you?")
    tree.add_node(root)

    child_a = DialogueNode(node_id="D2_A", speaker="Mayu", text="A traveler... welcome.")
    child_b = DialogueNode(node_id="D2_B", speaker="Mayu", text="A thief! Beware.")

    tree.add_branch("D1", "choice_truth", "I am a lost wanderer.", child_a)
    tree.add_branch("D1", "choice_lie", "I am the owner of this house.", child_b)

    # Sub-branch
    grandchild = DialogueNode(node_id="D3_A", speaker="Mayu", text="Warm yourself by the hearth.")
    tree.add_branch("D2_A", "choice_accept", "Thank you.", grandchild)

    # Pre-order DFS: Parent -> Child A -> Grandchild -> Child B
    order = [node.node_id for node in tree.preorder_traversal()]
    assert order == ["D1", "D2_A", "D3_A", "D2_B"]


def test_dialogue_choice_selection_and_effect_application():
    store = StateStore()
    store.init_character_emotions(1, {"trust": 50, "fear": 20})

    tree = DialogueTree()
    root = DialogueNode(node_id="D1", speaker="Ren", text="Tell me the truth.", character_id=1)
    tree.add_node(root)

    child = DialogueNode(
        node_id="D2",
        speaker="Aki",
        text="The spirit lives in the well.",
        character_id=1,
        effects={"emotions": {1: {"fear": 15}}},
    )

    tree.add_branch(
        parent_id="D1",
        choice_id="ask_spirit",
        choice_text="Where is the spirit?",
        child_node=child,
        choice_effects={"emotions": {1: {"trust": 10}}},
    )

    next_node, combined = tree.select_choice("D1", "ask_spirit", state_store=store)
    assert next_node.node_id == "D2"
    # Both choice effect (trust +10) and destination node effect (fear +15) applied
    emotions = store.get_emotions(1)
    assert emotions["trust"] == 60
    assert emotions["fear"] == 35


def test_invalid_choice_raises_error():
    tree = DialogueTree()
    root = DialogueNode(node_id="D1", speaker="Ren", text="Hello.")
    tree.add_node(root)

    with pytest.raises(ValueError, match="Choice 'nonexistent' not found"):
        tree.select_choice("D1", "nonexistent")
