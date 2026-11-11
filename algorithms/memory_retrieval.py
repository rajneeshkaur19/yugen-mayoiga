"""Keyword-based memory retrieval with bounded deque and top-k min-heap for Yūgen Mayoiga.

Architecture:
- Bounded deque for short-term memory sliding window (last N turns)
- Four memory types: short_term, long_term, emotional, player_choice
- Three statuses: normal, cracked, gilded
- Scoring formula: Score = Importance × Recency × Relevance
- Top-k retrieval using a min-heap of capacity k (time complexity: O(n log k))
- Deterministic keyword extraction and matching (no external AI/embedding dependency)
"""

from __future__ import annotations

import heapq
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Sequence


# Stop words for deterministic keyword matching
STOP_WORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were",
    "weren't", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "won't", "would", "wouldn't", "you", "your", "yours", "yourself",
})


def tokenize(text: str) -> set[str]:
    """Tokenize and normalize text into non-stop lowercase word tokens."""
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return {w for w in words if len(w) > 1 and w not in STOP_WORDS}


@dataclass
class MemoryRecord:
    """Represents a discrete memory stored in the memory system."""

    memory_id: int | str
    character_id: int
    event: str
    type: str  # "short_term", "long_term", "emotional", "player_choice"
    importance: int  # 0 to 100
    emotional_weight: int = 0  # -100 to 100
    status: str = "normal"  # "normal", "cracked", "gilded"
    created_turn: int = 0
    story_id: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ("short_term", "long_term", "emotional", "player_choice"):
            raise ValueError(f"Invalid memory type '{self.type}'")
        if self.status not in ("normal", "cracked", "gilded"):
            raise ValueError(f"Invalid memory status '{self.status}'")
        self.importance = max(0, min(100, self.importance))
        self.emotional_weight = max(-100, min(100, self.emotional_weight))
        self.created_turn = max(0, self.created_turn)


class MemoryStore:
    """Manages short-term and long-term memory with keyword-based top-k retrieval."""

    def __init__(self, short_term_capacity: int = 10) -> None:
        self.short_term_capacity = short_term_capacity
        self.short_term_window: deque[MemoryRecord] = deque(maxlen=short_term_capacity)
        self.all_memories: dict[int | str, MemoryRecord] = {}

    def add_memory(self, memory: MemoryRecord) -> None:
        """Add a memory to the store."""
        self.all_memories[memory.memory_id] = memory
        if memory.type == "short_term":
            self.short_term_window.append(memory)

    def promote_memory(
        self,
        memory_id: int | str,
        target_type: str = "long_term",
        new_status: str | None = None,
    ) -> MemoryRecord | None:
        """Promote a memory (e.g. from short_term to long_term or emotional)."""
        mem = self.all_memories.get(memory_id)
        if mem is None:
            return None
        mem.type = target_type
        if new_status:
            mem.status = new_status
        return mem

    # -------------------------------------------------------------------------
    # Scoring Functions
    # -------------------------------------------------------------------------

    @staticmethod
    def calculate_recency(created_turn: int, current_turn: int, decay_lambda: float = 0.05) -> float:
        """Calculate recency multiplier in range (0, 1].

        Uses hyperbolic decay: 1.0 / (1.0 + lambda * delta_turns).
        At delta=0, recency is 1.0. Older memories approach 0 gracefully.
        """
        delta = max(0, current_turn - created_turn)
        return 1.0 / (1.0 + decay_lambda * delta)

    @staticmethod
    def calculate_relevance(query_tokens: set[str], event_tokens: set[str]) -> float:
        """Calculate keyword relevance score between 0.0 and 1.0.

        Uses Jaccard overlap: |intersection| / |union|.
        If query is empty, returns baseline 0.5 (neutral relevance).
        """
        if not query_tokens:
            return 0.5
        intersection = query_tokens & event_tokens
        if not intersection:
            return 0.0
        union = query_tokens | event_tokens
        return len(intersection) / len(union)

    def score_memory(
        self,
        memory: MemoryRecord,
        query_tokens: set[str],
        current_turn: int,
    ) -> float:
        """Compute total score: Importance × Recency × Relevance.

        Kintsugi status bonus:
        - gilded: +20% boost
        - cracked: +10% emotional intensity boost
        """
        # Normalized importance (0.01 to 1.0 to avoid complete zeroing)
        norm_importance = max(0.01, memory.importance / 100.0)
        recency = self.calculate_recency(memory.created_turn, current_turn)
        event_tokens = tokenize(memory.event)
        relevance = self.calculate_relevance(query_tokens, event_tokens)

        # Baseline relevance for empty query so importance and recency still sort
        effective_relevance = relevance if query_tokens else 1.0

        raw_score = norm_importance * recency * effective_relevance

        # Status modifiers
        if memory.status == "gilded":
            raw_score *= 1.2
        elif memory.status == "cracked":
            raw_score *= 1.1

        return round(raw_score, 6)

    # -------------------------------------------------------------------------
    # Top-K Heap Retrieval: O(n log k)
    # -------------------------------------------------------------------------

    def retrieve_top_k(
        self,
        query: str,
        current_turn: int,
        k: int = 5,
        character_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryRecord, float]]:
        """Retrieve top-k relevant memories using a min-heap of size k.

        Time Complexity: O(n log k) where n is the number of eligible memories.
        Space Complexity: O(k) for the heap.
        Returns list of (MemoryRecord, score) sorted descending by score.
        """
        if k <= 0:
            return []

        query_tokens = tokenize(query)
        # Min-heap stores tuples: (score, tie_breaker, MemoryRecord)
        # We want to keep the k highest scores, so min-heap evicts the smallest
        heap: list[tuple[float, int, MemoryRecord]] = []
        counter = 0

        for mem in self.all_memories.values():
            if character_id is not None and mem.character_id != character_id:
                continue
            if memory_type is not None and mem.type != memory_type:
                continue

            score = self.score_memory(mem, query_tokens, current_turn)

            # Skip strictly zero relevance if a query was provided
            if query_tokens and score <= 0.0:
                continue

            counter += 1
            if len(heap) < k:
                heapq.heappush(heap, (score, counter, mem))
            else:
                if score > heap[0][0]:
                    heapq.heappushpop(heap, (score, counter, mem))

        # Extract elements and sort descending by score
        result: list[tuple[MemoryRecord, float]] = []
        while heap:
            score, _, mem = heapq.heappop(heap)
            result.append((mem, score))

        # Reverse to get highest scores first
        result.reverse()
        return result

    def retrieve_full_sort_reference(
        self,
        query: str,
        current_turn: int,
        k: int = 5,
        character_id: int | None = None,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryRecord, float]]:
        """Reference full-sort retrieval (O(n log n)) for unit test validation."""
        query_tokens = tokenize(query)
        scored: list[tuple[float, int, MemoryRecord]] = []
        counter = 0

        for mem in self.all_memories.values():
            if character_id is not None and mem.character_id != character_id:
                continue
            if memory_type is not None and mem.type != memory_type:
                continue

            score = self.score_memory(mem, query_tokens, current_turn)
            if query_tokens and score <= 0.0:
                continue

            counter += 1
            scored.append((score, counter, mem))

        scored.sort(key=lambda item: (-item[0], item[1]))
        top_k = scored[:k]
        return [(mem, score) for score, _, mem in top_k]
