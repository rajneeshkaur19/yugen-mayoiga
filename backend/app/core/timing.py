"""Pipeline stage timing and latency telemetry for Yūgen Mayoiga.

Tracks and logs execution latency for every stage of the gameplay action pipeline:
1. AI action interpretation
2. Deterministic action validation
3. State mutation / database operations
4. Narrative generation
5. Dynamic choice generation / cache retrieval
6. Provider fallback and model loading
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

logger = logging.getLogger("yugen.pipeline")

# Default console handler if not configured by root app
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


@contextmanager
def pipeline_timer(stage_name: str, extra: Optional[dict[str, Any]] = None) -> Generator[dict[str, Any], None, None]:
    """Context manager to measure and log execution latency for a pipeline stage."""
    t0 = time.perf_counter()
    info: dict[str, Any] = extra if extra is not None else {}
    try:
        yield info
    finally:
        elapsed = time.perf_counter() - t0
        info["duration_ms"] = round(elapsed * 1000, 2)
        info["duration_s"] = round(elapsed, 3)
        details = " | ".join(f"{k}={v}" for k, v in info.items() if k not in ("duration_ms", "duration_s"))
        detail_suffix = f" ({details})" if details else ""
        logger.info(f"[TIMING] {stage_name}: {elapsed:.3f}s{detail_suffix}")
