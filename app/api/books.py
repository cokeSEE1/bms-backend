from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_book_service
from app.schemas.book import BookOut
from app.services.book import BookService

router = APIRouter()


@router.get("/books")
async def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    limit: int = 20,
) -> list[BookOut]:
    books = await service.list_books(limit=limit)
    return [BookOut.model_validate(book) for book in books]
