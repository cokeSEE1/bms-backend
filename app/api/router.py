from fastapi import APIRouter

from app.api import auth, comment, directory, health, knowledge_item, ranking, upload, user_stats

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(directory.router, tags=["directory"])
api_router.include_router(knowledge_item.router, tags=["knowledge"])
api_router.include_router(comment.router, tags=["comments"])
api_router.include_router(user_stats.router, tags=["user"])
api_router.include_router(ranking.router, tags=["rankings"])
api_router.include_router(upload.router, tags=["upload"])
