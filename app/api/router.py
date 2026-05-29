from fastapi import APIRouter

from app.api import auth, directory, health, knowledge_item

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(directory.router, tags=["directory"])
api_router.include_router(knowledge_item.router, tags=["knowledge"])
