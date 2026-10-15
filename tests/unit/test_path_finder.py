
import pytest

from algorithms.path_finder import shortest_path, all_paths, can_reach_any


@pytest.fixture
def graph():
    return {
        "start": ["forest", "village"],
        "forest": ["ending"],
        "village": ["ending"],
        "ending": [],
        "dead_end": [],
    }


def test_shortest_path_returns_shortest_route(graph):
    assert shortest_path(graph, "start", "ending") == [
        "start", "forest", "ending"
    ]


def test_shortest_path_returns_none_when_unreachable(graph):
    assert shortest_path(graph, "start", "dead_end") is None


def test_shortest_path_handles_same_start_and_target(graph):
    assert shortest_path(graph, "start", "start") == ["start"]


def test_all_paths_returns_both_routes(graph):
    paths = all_paths(graph, "start", "ending")

    assert paths == [
        ["start", "forest", "ending"],
        ["start", "village", "ending"],
    ]


def test_all_paths_avoids_cycles():
    cyclic_graph = {
        "start": ["a"],
        "a": ["start", "ending"],
        "ending": [],
    }

    assert all_paths(cyclic_graph, "start", "ending") == [
        ["start", "a", "ending"]
    ]


def test_all_paths_respects_max_depth(graph):
    assert all_paths(graph, "start", "ending", max_depth=1) == []


def test_negative_max_depth_raises_error(graph):
    with pytest.raises(ValueError, match="max_depth"):
        all_paths(graph, "start", "ending", max_depth=-1)


def test_can_reach_any_target(graph):
    assert can_reach_any(graph, "start", ["dead_end", "ending"])


def test_returns_false_when_no_target_is_reachable(graph):
    assert not can_reach_any(graph, "start", ["dead_end"])


def test_start_can_itself_be_a_target(graph):
    assert can_reach_any(graph, "start", ["start"])
