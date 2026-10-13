
import pytest

from algorithms.story_graph import StoryGraph


@pytest.fixture
def story_graph():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("START", "LEAVE")
    graph.add_choice("HOUSE", "HALL")
    graph.add_choice("HALL", "ENDING")
    return graph


def test_add_scene():
    graph = StoryGraph()
    graph.add_scene("START")

    assert "START" in graph.graph
    assert graph.graph["START"] == []


def test_add_choice(story_graph):
    assert story_graph.get_choices("START") == ["HOUSE", "LEAVE"]


def test_bfs_shortest_distance(story_graph):
    assert story_graph.bfs_shortest_distance("START", "ENDING") == 3


def test_bfs_same_start_and_target(story_graph):
    assert story_graph.bfs_shortest_distance("START", "START") == 0


def test_bfs_unreachable_scene(story_graph):
    story_graph.add_scene("ISOLATED")

    assert story_graph.bfs_shortest_distance("START", "ISOLATED") == -1


def test_dfs_traversal(story_graph):
    assert story_graph.dfs_traversal("START") == [
        "START", "HOUSE", "HALL", "ENDING", "LEAVE"
    ]


def test_dfs_unknown_scene(story_graph):
    assert story_graph.dfs_traversal("UNKNOWN") == []


def test_dfs_with_cycle():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("HOUSE", "HALL")
    graph.add_choice("HALL", "START")

    assert graph.dfs_traversal("START") == ["START", "HOUSE", "HALL"]

def test_can_reach_ending(story_graph):
    assert story_graph.can_reach_ending("START", "ENDING") is True


def test_cannot_reach_unconnected_ending(story_graph):
    story_graph.add_scene("ISOLATED")

    assert story_graph.can_reach_ending("START", "ISOLATED") is False


def test_unknown_scene_cannot_reach_ending(story_graph):
    assert story_graph.can_reach_ending("UNKNOWN", "ENDING") is False


def test_find_dead_ends():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("HOUSE", "ENDING")
    graph.add_choice("START", "BASEMENT")

    assert graph.find_dead_ends({"ENDING"}) == ["BASEMENT"]


def test_find_dead_ends_ignores_valid_endings():
    graph = StoryGraph()
    graph.add_scene("ENDING")

    assert graph.find_dead_ends({"ENDING"}) == []


def test_find_dead_ends_returns_empty_for_valid_graph():
    graph = StoryGraph()
    graph.add_choice("START", "ENDING")

    assert graph.find_dead_ends({"ENDING"}) == []


def test_find_dead_ends_with_multiple_dead_ends():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("START", "BASEMENT")
    graph.add_scene("ENDING")

    assert graph.find_dead_ends({"ENDING"}) == ["HOUSE", "BASEMENT"]


def test_has_cycle_returns_false_for_acyclic_graph():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("HOUSE", "ENDING")

    assert graph.has_cycle() is False


def test_has_cycle_returns_true_for_cycle():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("HOUSE", "HALL")
    graph.add_choice("HALL", "START")

    assert graph.has_cycle() is True


def test_has_cycle_detects_self_loop():
    graph = StoryGraph()
    graph.add_choice("HOUSE", "HOUSE")

    assert graph.has_cycle() is True


def test_has_cycle_returns_false_for_empty_graph():
    graph = StoryGraph()

    assert graph.has_cycle() is False


def test_find_all_paths_returns_all_routes():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("START", "GARDEN")
    graph.add_choice("HOUSE", "ENDING")
    graph.add_choice("GARDEN", "ENDING")

    assert graph.find_all_paths("START", "ENDING") == [
        ["START", "HOUSE", "ENDING"],
        ["START", "GARDEN", "ENDING"],
    ]


def test_find_all_paths_returns_empty_when_unreachable():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_scene("ENDING")

    assert graph.find_all_paths("START", "ENDING") == []


def test_find_all_paths_same_start_and_target():
    graph = StoryGraph()
    graph.add_scene("START")

    assert graph.find_all_paths("START", "START") == [["START"]]


def test_find_all_paths_handles_cycles():
    graph = StoryGraph()
    graph.add_choice("START", "HOUSE")
    graph.add_choice("HOUSE", "START")
    graph.add_choice("HOUSE", "ENDING")

    assert graph.find_all_paths("START", "ENDING") == [
        ["START", "HOUSE", "ENDING"]
    ]


def test_find_all_paths_unknown_start():
    graph = StoryGraph()
    graph.add_scene("ENDING")

    assert graph.find_all_paths("UNKNOWN", "ENDING") == []

