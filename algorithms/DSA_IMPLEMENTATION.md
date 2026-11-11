# Yūgen Mayoiga — DSA Implementation Reference

This document tracks all data structures and algorithms implemented across the Yūgen Mayoiga engine.

## Summary Table

| Module | Core Technique | Purpose | Time Complexity | Space Complexity |
|---|---|---|---|---|
| `story_graph.py` | Adjacency list, BFS, DFS | Scene & choice graph navigation, shortest path, dead ends | Add: $O(1)$, Traversal: $O(V+E)$ | $O(V+E)$ |
| `path_finder.py` | Graph traversal & cycle detection | 3-color DFS cycle detector, reachability validation | $O(V+E)$ | $O(V+E)$ |
| `history_stack.py` | Stack of StateDeltas | Reversible attribute and dict-entry undo | Push/Pop: $O(1)$ | $O(\Delta)$ |
| `priority_events.py` | Two heaps + FIFO queue | Min-heap by turn + max-heap by priority | Push/Pop: $O(\log n)$ | $O(n)$ |
| `state_store.py` | Hash map with clamping & decay | Emotions, relationships, world state, hidden variables | $O(1)$ average | $O(S)$ |
| `dialogue_tree.py` | Multi-way tree, pre-order DFS | Branching dialogue nodes with effect execution | Traversal: $O(n)$ | $O(n)$ |
| `memory_retrieval.py` | Bounded deque + top-$k$ min-heap | Importance $\times$ Recency $\times$ Relevance memory scoring | Insertion: $O(1)$, Top-$k$: $O(n \log k)$ | $O(k)$ heap |
| `lru_cache.py` | Hash map + Doubly Linked List | Plan/scene cache | Get/Put: $O(1)$ | $O(C)$ |

---

## 1. Dialogue Tree (`algorithms/dialogue_tree.py`)

- **Structure**: Each `DialogueNode` encapsulates speaker, spoken text, character binding, effects, and outgoing `DialogueChoice` branches.
- **Traversal**: Pre-order depth-first traversal visits parent nodes before children.
- **Effects Application**: Selecting a choice deterministically combines choice effects and child node effects, updating character emotions and relationships in $O(1)$.
- **Time Complexity**: Tree traversal runs in $O(n)$ where $n$ is the total dialogue nodes.

---

## 2. Memory Retrieval (`algorithms/memory_retrieval.py`)

- **Short-term Window**: Implemented using `collections.deque(maxlen=N)`, preserving the most recent $N$ short-term events in $O(1)$ amortized push.
- **Scoring Model**:
  $$\text{Score} = \text{Importance} \times \text{Recency} \times \text{Relevance}$$
  - **Importance**: $\frac{\text{importance}}{100.0}$
  - **Recency**: Hyperbolic decay: $\frac{1}{1 + \lambda \cdot (\text{current\_turn} - \text{created\_turn})}$
  - **Relevance**: Jaccard similarity between query tokens and memory event tokens.
  - **Kintsugi Modifier**: Gilded memories receive a $+20\%$ boost; cracked memories receive $+10\%$.
- **Top-$k$ Min-Heap Selection**: Instead of sorting all $n$ memories in $O(n \log n)$, a min-heap of capacity $k$ processes items in a single pass. Evicting the minimum score element when heap size exceeds $k$ guarantees top-$k$ retrieval in $O(n \log k)$ time and $O(k)$ auxiliary space.

---

## 3. State Store (`algorithms/state_store.py`)

- **Emotion Management**: 6 Big-Five-derived emotions clamped between 0 and 100.
- **Decay Algorithm**: Configurable drift rate pulling heightened/depressed emotions toward baseline per scene transition.
- **Memory Reinforcement**: Emotional memories dampen or counteract decay based on importance and emotional weight.
- **Relationship Management**: Directed graph pairs `(from_char, to_char)` with non-reflexive integrity.
- **World State**: Key-value store for story progression variables.
- **Yūgen Meter**: 0–100 mystery tracking counter adjusted by discovery/obscurity deltas.
