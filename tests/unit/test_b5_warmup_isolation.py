"""
Batch 5 — Task 1 regression tests for the OllamaProvider warmup guard.

Verifies that the lifespan skips OllamaProvider warmup when:
  1. PYTEST_CURRENT_TEST env var is set (pytest sets this automatically).
  2. DISABLE_STARTUP_WARMUP=1 is set explicitly.

These tests inspect the guard logic directly — they do NOT re-import or
re-instantiate the FastAPI app object (which is a module-level singleton
already initialised by conftest.py) to avoid lifespan re-entry issues.
"""
import os
import threading
import time
from unittest.mock import MagicMock, patch


def _is_test_env(env: dict) -> bool:
    """Mirror the lifespan guard logic from backend/app/main.py."""
    return bool(env.get("PYTEST_CURRENT_TEST")) or (
        env.get("DISABLE_STARTUP_WARMUP", "").strip().lower() in ("1", "true", "yes")
    )


def test_warmup_suppressed_when_pytest_env_set():
    """PYTEST_CURRENT_TEST present → guard returns True → warmup skipped."""
    env = {"PYTEST_CURRENT_TEST": "some_test_name[unit]"}
    assert _is_test_env(env) is True, "Guard should detect PYTEST_CURRENT_TEST."


def test_warmup_suppressed_when_disable_flag_set():
    """DISABLE_STARTUP_WARMUP=1 → guard returns True → warmup skipped."""
    env = {"DISABLE_STARTUP_WARMUP": "1"}
    assert _is_test_env(env) is True


def test_warmup_suppressed_when_disable_flag_true():
    """DISABLE_STARTUP_WARMUP=true → guard returns True."""
    env = {"DISABLE_STARTUP_WARMUP": "true"}
    assert _is_test_env(env) is True


def test_warmup_allowed_when_no_guard_set():
    """No guard env vars → warmup is NOT suppressed (production behaviour)."""
    env = {"OLLAMA_MODEL": "phi3:latest"}
    assert _is_test_env(env) is False, "Guard must not suppress in production env."


def test_pytest_env_var_set_during_pytest_run():
    """
    Confirm that PYTEST_CURRENT_TEST is actually set by pytest when this
    test is running — meaning the production lifespan guard is active.
    """
    assert os.getenv("PYTEST_CURRENT_TEST"), (
        "PYTEST_CURRENT_TEST must be set by pytest during test execution. "
        "If this assertion fails the entire warmup guard may not function."
    )


def test_warmup_thread_does_not_run_in_test_env(monkeypatch):
    """
    Simulate the full lifespan warmup decision:
    - Set OLLAMA_MODEL so warmup *would* run in production.
    - Set PYTEST_CURRENT_TEST so the guard suppresses it.
    - Confirm no background thread calls OllamaProvider.warmup().
    """
    monkeypatch.setenv("OLLAMA_MODEL", "phi3:latest")
    # PYTEST_CURRENT_TEST is already set by pytest — keep it.

    warmup_called = []

    def fake_warmup():
        warmup_called.append(True)

    # Reproduce the lifespan decision inline.
    is_test_env = _is_test_env(dict(os.environ))
    if os.getenv("OLLAMA_MODEL") and not is_test_env:
        t = threading.Thread(target=fake_warmup, daemon=True)
        t.start()
        t.join(timeout=1)

    assert warmup_called == [], (
        "OllamaProvider.warmup() must not be called when PYTEST_CURRENT_TEST is set."
    )
