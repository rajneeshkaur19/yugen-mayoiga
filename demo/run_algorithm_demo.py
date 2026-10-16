"""Demonstrate Week 2 graph algorithms and data structures."""

from algorithms.story_graph import StoryGraph
from algorithms.path_finder import shortest_path, all_paths
from algorithms.priority_events import (
    PriorityEventManager,
    StoryEvent,
)
from algorithms.history_stack import HistoryStack, StateDelta


def demo_graph_algorithms() -> None:
    print("\n" + "=" * 60)
    print("1. STORY GRAPH: BFS, DFS, PATHS, DEAD ENDS & CYCLES")
    print("=" * 60)

    graph = StoryGraph()

    edges = [
        ("SHRINE", "FOREST"),
        ("SHRINE", "VILLAGE"),
        ("FOREST", "TRUTH"),
        ("FOREST", "SILENCE"),
        ("VILLAGE", "TRUTH"),
        ("VILLAGE", "TRAP"),
    ]

    for source, target in edges:
        graph.add_choice(source, target)

    # Explicitly add an ending node with no outgoing choices.
    graph.add_scene("TRAP")
    graph.add_scene("TRUTH")
    graph.add_scene("SILENCE")

    graph.display_graph()

    print("\nBFS shortest distance SHRINE -> TRUTH:",
          graph.bfs_shortest_distance("SHRINE", "TRUTH"))

    print("DFS traversal from SHRINE:",
          graph.dfs_traversal("SHRINE"))

    print("Shortest path SHRINE -> TRUTH:",
          shortest_path(graph.graph, "SHRINE", "TRUTH"))

    print("All simple paths SHRINE -> TRUTH:")
    for path in all_paths(graph.graph, "SHRINE", "TRUTH"):
        print("  " + " -> ".join(path))

    print("Can reach TRUTH from SHRINE:",
          graph.can_reach_ending("SHRINE", "TRUTH"))

    print("Dead ends (excluding endings):",
          graph.find_dead_ends({"TRUTH", "SILENCE"}))

    print("Contains a cycle:", graph.has_cycle())

    # Demonstrate cycle detection on a separate graph.
    cyclic_graph = StoryGraph()
    cyclic_graph.add_choice("A", "B")
    cyclic_graph.add_choice("B", "C")
    cyclic_graph.add_choice("C", "A")
    print("Cycle detection on A -> B -> C -> A:",
          cyclic_graph.has_cycle())


def demo_undo_stack() -> None:
    print("\n" + "=" * 60)
    print("2. HISTORY STACK: LIFO UNDO")
    print("=" * 60)

    class DemoState:
        def __init__(self) -> None:
            self.scene = "SHRINE"
            self.traits = {"courage": 50}

    state = DemoState()
    history = HistoryStack()

    print("Initial state:", state.scene, state.traits)

    old_scene = state.scene
    state.scene = "FOREST"
    state.traits["courage"] = 55

    history.push([
        StateDelta.for_attribute(
            state, "scene", old_scene, state.scene
        ),
        StateDelta.for_dict_entry(
            target=state,
            attribute="traits",
            key="courage",
            old_value=50,
            new_value=55,
        ),
    ])

    print("After choice:", state.scene, state.traits)

    history.undo()
    print("After undo:", state.scene, state.traits)
    print("Undo history empty:", history.is_empty())


def demo_priority_events() -> None:
    print("\n" + "=" * 60)
    print("3. EVENT SCHEDULING: QUEUE + HEAPS")
    print("=" * 60)

    manager = PriorityEventManager()

    manager.add_event(
        StoryEvent("whisper", due_time=2, priority=3,
                   payload="A voice whispers your name.")
    )
    manager.add_event(
        StoryEvent("storm", due_time=1, priority=1,
                   payload="The storm grows stronger.")
    )
    manager.add_event(
        StoryEvent("lantern", due_time=2, priority=5,
                   payload="The lantern suddenly brightens.")
    )

    print("Pending events:", len(manager.pending))
    print("Scheduled:", manager.schedule_pending())
    print("Next scheduled event:", manager.peek_next_scheduled().event_id)

    print("Events promoted at time 1:",
          manager.promote_due_events(current_time=1))

    event = manager.pop_ready_event()
    print("Ready event at time 1:",
          event.event_id if event else None)

    print("Events promoted at time 2:",
          manager.promote_due_events(current_time=2))

    print("Ready events by priority:")
    while True:
        event = manager.pop_ready_event()
        if event is None:
            break
        print(
            f"  priority={event.priority}: "
            f"{event.event_id} — {event.payload}"
        )


def main() -> None:
    print("\nYUGEN MAYOIGA — WEEK 2 ALGORITHM DEMO")
    demo_graph_algorithms()
    demo_undo_stack()
    demo_priority_events()
    print("\nDemo completed.")


if __name__ == "__main__":
    main()
