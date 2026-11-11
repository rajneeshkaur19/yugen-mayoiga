"""Ending Engine for Yūgen Mayoiga.

Handles:
- Storage and validation of ending definitions
- Deterministic evaluation of ending conditions against story state
- Recording achieved endings in user_endings table
- Multiple ending detection and duplicate prevention
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.ending import Ending
from backend.app.models.user_ending import UserEnding


def evaluate_condition_clause(clause_key: str, clause_rule: Any, current_state: dict[str, Any]) -> bool:
    """Evaluate one condition clause against current state dictionary.

    Supports:
    - Direct equality: {"truth_discovered": True} -> state["truth_discovered"] == True
    - Operator dict: {"trust": {">": 70}} -> state["trust"] > 70
    - Operator dict: {"fear": {"<=": 20}} -> state["fear"] <= 20
    - Operator dict: {"power": {"!=": "off"}} -> state["power"] != "off"
    """
    actual_val = current_state.get(clause_key)

    # 1. If rule is a dict of operators like {">": 70, "<=": 100}
    if isinstance(clause_rule, dict):
        if actual_val is None:
            return False
        for op, target in clause_rule.items():
            if op in (">", "gt"):
                if not (actual_val > target):
                    return False
            elif op in (">=", "gte"):
                if not (actual_val >= target):
                    return False
            elif op in ("<", "lt"):
                if not (actual_val < target):
                    return False
            elif op in ("<=", "lte"):
                if not (actual_val <= target):
                    return False
            elif op in ("==", "eq"):
                if not (actual_val == target):
                    return False
            elif op in ("!=", "ne"):
                if not (actual_val != target):
                    return False
            elif op == "in":
                if actual_val not in target:
                    return False
            elif op == "not_in":
                if actual_val in target:
                    return False
            else:
                # Unsupported operator
                return False
        return True

    # 2. Direct equality / presence
    if isinstance(clause_rule, bool):
        return bool(actual_val) is clause_rule

    return actual_val == clause_rule


def evaluate_ending(ending: Ending, state: dict[str, Any]) -> bool:
    """Evaluate whether an ending's conditions are fully satisfied by current state.

    All top-level keys in ending.conditions must evaluate to True (logical AND).
    """
    conditions = ending.conditions
    if not isinstance(conditions, dict) or not conditions:
        return False

    for key, rule in conditions.items():
        if not evaluate_condition_clause(key, rule, state):
            return False

    return True


def create_ending(
    db: Session,
    story_id: int,
    name: str,
    conditions: dict[str, Any],
    seal_text: str,
) -> Ending:
    """Define a possible ending for a story playthrough."""
    ending = Ending(
        story_id=story_id,
        name=name,
        conditions=conditions,
        seal_text=seal_text,
    )
    try:
        db.add(ending)
        db.commit()
        db.refresh(ending)
        return ending
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(f"An ending named '{name}' already exists for story {story_id}.") from exc
    except Exception:
        db.rollback()
        raise


def list_story_endings(db: Session, story_id: int) -> list[Ending]:
    """Return all ending definitions configured for a story."""
    return list(
        db.scalars(
            select(Ending)
            .where(Ending.story_id == story_id)
            .order_by(Ending.id)
        ).all()
    )



def record_achieved_ending(
    db: Session,
    user_id: int,
    ending_id: int,
) -> UserEnding | None:
    """Stage an achieved ending inside the caller's transaction.

    A savepoint protects duplicate inserts without committing or rolling
    back the surrounding story-action transaction.
    """
    existing = db.scalar(
        select(UserEnding).where(
            UserEnding.user_id == user_id,
            UserEnding.ending_id == ending_id,
        )
    )
    if existing is not None:
        return existing

    record = UserEnding(user_id=user_id, ending_id=ending_id)
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
        return record
    except IntegrityError:
        return db.scalar(
            select(UserEnding).where(
                UserEnding.user_id == user_id,
                UserEnding.ending_id == ending_id,
            )
        )



def check_and_trigger_endings(
    db: Session,
    story_id: int,
    user_id: int,
    current_state: dict[str, Any],
) -> list[Ending]:
    """Check all story endings against current state and record any newly achieved ones."""
    endings = list_story_endings(db, story_id)
    achieved: list[Ending] = []

    for end in endings:
        if evaluate_ending(end, current_state):
            record_achieved_ending(db, user_id, end.id)
            achieved.append(end)

    return achieved


def get_user_endings(db: Session, user_id: int) -> list[UserEnding]:
    """Retrieve all endings achieved by a user."""
    return list(
        db.scalars(
            select(UserEnding)
            .where(UserEnding.user_id == user_id)
            .order_by(UserEnding.achieved_at.desc())
        ).all()
    )
