"""Dialogue Tree data structure and pre-order traversal for Yūgen Mayoiga.

Enables branching conversations within scenes. Each dialogue node can have:
- Speaker identifier and character reference
- Spoken text or dialogue prompt
- Child choices or continuation branches
- Configured emotion/relationship effects applied when reached
- Pre-order traversal O(n)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterator


@dataclass
class DialogueChoice:
    """An edge leading from a dialogue node to a child node."""

    choice_id: str
    text: str
    target_node_id: str
    condition: dict[str, Any] | None = None
    effects: dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueNode:
    """A single node within a dialogue tree."""

    node_id: str
    speaker: str
    text: str
    character_id: int | None = None
    effects: dict[str, Any] = field(default_factory=dict)
    choices: list[DialogueChoice] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_choice(
        self,
        choice_id: str,
        text: str,
        target_node_id: str,
        condition: dict[str, Any] | None = None,
        effects: dict[str, Any] | None = None,
    ) -> DialogueChoice:
        """Add a branching choice from this node."""
        choice = DialogueChoice(
            choice_id=choice_id,
            text=text,
            target_node_id=target_node_id,
            condition=condition,
            effects=effects or {},
        )
        self.choices.append(choice)
        return choice


@dataclass
class DialogueTree:
    """A rooted tree of dialogue nodes representing an interactive conversation."""

    root_id: str | None = None
    nodes: dict[str, DialogueNode] = field(default_factory=dict)

    def add_node(self, node: DialogueNode) -> None:
        """Add a node to the dialogue tree."""
        if not self.root_id:
            self.root_id = node.node_id
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> DialogueNode | None:
        """Retrieve a node by its identifier."""
        return self.nodes.get(node_id)

    def get_root(self) -> DialogueNode | None:
        """Return the root dialogue node."""
        if self.root_id is None:
            return None
        return self.nodes.get(self.root_id)

    def add_branch(
        self,
        parent_id: str,
        choice_id: str,
        choice_text: str,
        child_node: DialogueNode,
        choice_effects: dict[str, Any] | None = None,
        condition: dict[str, Any] | None = None,
    ) -> None:
        """Add a child node and connect it to a parent node via a choice edge."""
        if parent_id not in self.nodes:
            raise KeyError(f"Parent node '{parent_id}' does not exist in tree.")
        self.add_node(child_node)
        parent = self.nodes[parent_id]
        parent.add_choice(
            choice_id=choice_id,
            text=choice_text,
            target_node_id=child_node.node_id,
            condition=condition,
            effects=choice_effects,
        )

    def preorder_traversal(
        self,
        start_node_id: str | None = None,
    ) -> list[DialogueNode]:
        """Traverse the dialogue tree in pre-order: Parent -> Children (O(n))."""
        start = start_node_id or self.root_id
        if not start or start not in self.nodes:
            return []

        visited: set[str] = set()
        result: list[DialogueNode] = []

        def _dfs(current_id: str) -> None:
            if current_id in visited or current_id not in self.nodes:
                return
            visited.add(current_id)
            node = self.nodes[current_id]
            result.append(node)
            for choice in node.choices:
                _dfs(choice.target_node_id)

        _dfs(start)
        return result

    def select_choice(
        self,
        current_node_id: str,
        choice_id: str,
        state_store: Any | None = None,
    ) -> tuple[DialogueNode, dict[str, Any]]:
        """Select a choice from the current node.

        Returns (next_node, combined_effects).
        If a state_store is provided, applies choice and node effects directly.
        """
        node = self.get_node(current_node_id)
        if node is None:
            raise KeyError(f"Current node '{current_node_id}' does not exist.")

        selected: DialogueChoice | None = None
        for ch in node.choices:
            if ch.choice_id == choice_id:
                selected = ch
                break

        if selected is None:
            raise ValueError(f"Choice '{choice_id}' not found on node '{current_node_id}'.")

        next_node = self.get_node(selected.target_node_id)
        if next_node is None:
            raise KeyError(f"Target node '{selected.target_node_id}' does not exist.")

        def _deep_merge(target: dict, source: dict) -> dict:
            out = dict(target)
            for k, v in source.items():
                if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                    out[k] = _deep_merge(out[k], v)
                else:
                    out[k] = v
            return out

        combined_effects = _deep_merge(selected.effects, next_node.effects)

        if state_store is not None and hasattr(state_store, "apply_choice_effects"):
            state_store.apply_choice_effects(
                combined_effects,
                active_character_id=next_node.character_id,
            )

        return next_node, combined_effects
