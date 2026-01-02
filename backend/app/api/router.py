from fastapi import APIRouter

from app.api.routes import auth, dialogue, emotion, health, history, music, search, social, ui
from app.api.routes import works

api_router = APIRouter()

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(music.router, prefix="/music", tags=["music"])
api_router.include_router(emotion.router, prefix="/emotion", tags=["emotion"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(dialogue.router, prefix="/dialogues", tags=["dialogues"])
api_router.include_router(ui.router, prefix="/ui", tags=["ui"])
api_router.include_router(works.router, prefix="/works", tags=["works"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
