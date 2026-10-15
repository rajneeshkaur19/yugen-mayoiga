
"""Path-finding utilities for the Yugen Mayoiga story graph."""

from collections import deque
from typing import Hashable, Iterable, Mapping, TypeVar

Node = TypeVar("Node", bound=Hashable)


def shortest_path(
    graph: Mapping[Node, Iterable[Node]],
    start: Node,
    target: Node,
) -> list[Node] | None:
    """Return the shortest path using BFS, or None if unreachable."""
    if start not in graph or target not in graph:
        return None

    queue = deque([start])
    parent: dict[Node, Node | None] = {start: None}

    while queue:
        current = queue.popleft()

        if current == target:
            path: list[Node] = []
            node: Node | None = current

            while node is not None:
                path.append(node)
                node = parent[node]

            return list(reversed(path))

        for neighbor in graph.get(current, ()):
            if neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)

    return None


def all_paths(
    graph: Mapping[Node, Iterable[Node]],
    start: Node,
    target: Node,
    *,
    max_depth: int = 100,
) -> list[list[Node]]:
    """Return simple paths from start to target without repeating nodes."""
    if max_depth < 0:
        raise ValueError("max_depth cannot be negative.")

    if start not in graph or target not in graph:
        return []

    results: list[list[Node]] = []
    path: list[Node] = [start]
    visited: set[Node] = {start}

    def dfs(current: Node) -> None:
        if current == target:
            results.append(path.copy())
            return

        if len(path) - 1 >= max_depth:
            return

        for neighbor in graph.get(current, ()):
            if neighbor in visited:
                continue

            visited.add(neighbor)
            path.append(neighbor)
            dfs(neighbor)
            path.pop()
            visited.remove(neighbor)

    dfs(start)
    return results


def can_reach_any(
    graph: Mapping[Node, Iterable[Node]],
    start: Node,
    targets: Iterable[Node],
) -> bool:
    """Return whether any target is reachable from start."""
    target_set = set(targets)

    if start not in graph:
        return False

    if start in target_set:
        return True

    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()

        for neighbor in graph.get(current, ()):
            if neighbor in target_set:
                return True

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return False
