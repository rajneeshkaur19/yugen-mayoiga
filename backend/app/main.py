from fastapi import FastAPI

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

app = FastAPI(
    title="Yūgen Mayoiga",
    description="Interactive, Stateful Narrative Intelligence Platform — Milestone M2",
    version="0.4.0",
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
