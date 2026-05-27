from fastapi import APIRouter

from app.api import auth, books, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(books.router, tags=["books"])
api_router.include_router(auth.router, tags=["auth"])
