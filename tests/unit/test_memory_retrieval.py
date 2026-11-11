import pytest
from algorithms.memory_retrieval import MemoryRecord, MemoryStore


def test_memory_creation_and_validation():
    # Valid types
    for mtype in ("short_term", "long_term", "emotional", "player_choice"):
        mem = MemoryRecord(
            memory_id=1,
            character_id=1,
            event="Discovered an iron key in the garden.",
            type=mtype,
            importance=80,
            emotional_weight=20,
            status="normal",
            created_turn=1,
        )
        assert mem.type == mtype

    # Invalid type raises
    with pytest.raises(ValueError, match="Invalid memory type"):
        MemoryRecord(memory_id=2, character_id=1, event="x", type="invalid", importance=50)

    # Invalid status raises
    with pytest.raises(ValueError, match="Invalid memory status"):
        MemoryRecord(memory_id=3, character_id=1, event="x", type="short_term", importance=50, status="bad")


def test_short_term_bounded_deque():
    store = MemoryStore(short_term_capacity=3)
    for i in range(5):
        store.add_memory(
            MemoryRecord(
                memory_id=i,
                character_id=1,
                event=f"Event {i}",
                type="short_term",
                importance=50,
                created_turn=i,
            )
        )

    # Only last 3 remain in sliding window
    window_ids = [m.memory_id for m in store.short_term_window]
    assert window_ids == [2, 3, 4]
    # But all 5 exist in all_memories
    assert len(store.all_memories) == 5


def test_recency_scoring():
    # Immediate turn -> recency is 1.0
    r0 = MemoryStore.calculate_recency(created_turn=10, current_turn=10)
    assert r0 == 1.0

    # 10 turns later -> recency decayed
    r10 = MemoryStore.calculate_recency(created_turn=0, current_turn=10)
    assert 0.0 < r10 < 1.0
    assert r10 == 1.0 / (1.0 + 0.05 * 10)

    # 50 turns later -> decayed further
    r50 = MemoryStore.calculate_recency(created_turn=0, current_turn=50)
    assert r50 < r10


def test_keyword_relevance_scoring():
    # High overlap
    q_tokens = {"iron", "key", "well"}
    e_tokens = {"iron", "key", "garden"}
    rel = MemoryStore.calculate_relevance(q_tokens, e_tokens)
    # intersection = {"iron", "key"} (2), union = {"iron", "key", "well", "garden"} (4) -> 0.5
    assert rel == 0.5

    # Zero overlap
    rel_zero = MemoryStore.calculate_relevance(q_tokens, {"tea", "cup"})
    assert rel_zero == 0.0


def test_memory_promotion_and_status():
    store = MemoryStore()
    mem = MemoryRecord(
        memory_id=1,
        character_id=1,
        event="Heard a whisper in the dark.",
        type="short_term",
        importance=85,
        status="normal",
    )
    store.add_memory(mem)

    # Promote to emotional with gilded status
    promoted = store.promote_memory(1, target_type="emotional", new_status="gilded")
    assert promoted is not None
    assert promoted.type == "emotional"
    assert promoted.status == "gilded"


def test_heap_top_k_matches_full_sort_reference():
    """Verify O(n log k) min-heap top-k retrieval matches full sort O(n log n) reference."""
    store = MemoryStore()
    memories_data = [
        ("The iron key fits the cellar door perfectly.", 90, 1),
        ("A cup of hot green tea was served by the monk.", 30, 2),
        ("Heard faint crying near the old stone well at midnight.", 85, 3),
        ("The spirit of the well warned about the red shrine.", 95, 4),
        ("Rain began falling on the cedar shingles.", 20, 5),
        ("Found an old photograph hidden behind the shrine altar.", 75, 6),
        ("The cellar was locked with an ancient bronze chain.", 70, 7),
        ("Shadows lengthened as the sun dipped behind Mount Mayoiga.", 40, 8),
        ("A mysterious woman appeared carrying a paper lantern.", 80, 9),
        ("The iron key shattered inside the rusted lock.", 85, 10),
    ]

    for idx, (event, imp, turn) in enumerate(memories_data, start=1):
        store.add_memory(
            MemoryRecord(
                memory_id=idx,
                character_id=1,
                event=event,
                type="long_term",
                importance=imp,
                created_turn=turn,
            )
        )

    query = "iron key cellar locked shrine"
    current_turn = 12
    k = 4

    heap_results = store.retrieve_top_k(query=query, current_turn=current_turn, k=k)
    sort_results = store.retrieve_full_sort_reference(query=query, current_turn=current_turn, k=k)

    assert len(heap_results) == k
    assert len(sort_results) == k

    heap_ids = [m.memory_id for m, _ in heap_results]
    sort_ids = [m.memory_id for m, _ in sort_results]
    assert heap_ids == sort_ids

    heap_scores = [round(score, 4) for _, score in heap_results]
    sort_scores = [round(score, 4) for _, score in sort_results]
    assert heap_scores == sort_scores
