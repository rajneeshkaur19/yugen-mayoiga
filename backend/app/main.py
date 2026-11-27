import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.characters import router as characters_router
from backend.app.api.choices import router as choices_router
from backend.app.api.endings import router as endings_router
from backend.app.api.memories import router as memories_router
from backend.app.api.relationships import router as relationships_router
from backend.app.api.scenes import router as scenes_router
from backend.app.api.state import router as state_router
from backend.app.api.stories import router as stories_router
from backend.app.api.world_state import router as world_state_router
from backend.app.api.ai import router as ai_router
from backend.app.api.feedback import router as feedback_router
from starlette.staticfiles import StaticFiles
from backend.app.services.image_generation_service import IMAGE_STORAGE_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Background startup hooks to optimize local AI fallback."""
    warmup_thread: threading.Thread | None = None
    is_test_env = bool(os.getenv("PYTEST_CURRENT_TEST")) or (
        os.getenv("DISABLE_STARTUP_WARMUP", "").strip().lower() in ("1", "true", "yes")
    )
    if os.getenv("OLLAMA_MODEL") and not is_test_env:
        def _bg_warmup():
            try:
                from backend.app.ai.providers import OllamaProvider
                provider = OllamaProvider()
                provider.warmup()
            except Exception:
                pass
        warmup_thread = threading.Thread(target=_bg_warmup, daemon=True)
        warmup_thread.start()
    yield
    if warmup_thread is not None and warmup_thread.is_alive():
        warmup_thread.join(timeout=0.5)


app = FastAPI(
    title="Yūgen Mayoiga",
    description="Interactive, Stateful Narrative Intelligence Platform — Milestone M2",
    version="0.4.0",
    lifespan=lifespan,
)

_cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(stories_router)
app.include_router(characters_router)
app.include_router(scenes_router)
app.include_router(choices_router)
app.include_router(memories_router)
app.include_router(relationships_router)
app.include_router(world_state_router)
app.include_router(endings_router)
app.include_router(state_router)
app.include_router(ai_router)
app.include_router(feedback_router)

# Serve generated images from storage directory
IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated-images", StaticFiles(directory=str(IMAGE_STORAGE_DIR)), name="generated-images")
app.mount("/api/generated-images", StaticFiles(directory=str(IMAGE_STORAGE_DIR)), name="api-generated-images")


@app.get("/")
def root():
    return {
        "project": "Yūgen Mayoiga",
        "status": "running",
        "milestone": "M2: Full backend and persistent state",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
