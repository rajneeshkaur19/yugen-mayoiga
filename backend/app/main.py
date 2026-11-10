from fastapi import FastAPI

from backend.app.api.auth import router as auth_router
from backend.app.api.characters import router as characters_router
from backend.app.api.choices import router as choices_router
from backend.app.api.memories import router as memories_router
from backend.app.api.scenes import router as scenes_router
from backend.app.api.stories import router as stories_router

app = FastAPI(
    title="Yūgen Mayoiga",
    description="Interactive, Stateful Narrative Intelligence Platform",
    version="0.3.0",
)

app.include_router(auth_router)
app.include_router(stories_router)
app.include_router(characters_router)
app.include_router(scenes_router)
app.include_router(choices_router)
app.include_router(memories_router)


@app.get("/")
def root():
    return {
        "project": "Yūgen Mayoiga",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
