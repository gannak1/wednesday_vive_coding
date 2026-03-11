from typing import Any

from app.core.constants import CATEGORIES, CONTINENTS
from app.core.exceptions import InvalidCategoryError, InvalidContinentError, NewsNotFoundError, SavedArticleNotFoundError
from app.repositories.news_repository import NewsRepository
from app.repositories.saved_repository import SavedRepository


class SavedArticlesService:
    def __init__(self, database: Any) -> None:
        self.news_repository = NewsRepository(database)
        self.saved_repository = SavedRepository(database)

    async def save_article(self, session_id: str, article_id: str) -> dict[str, Any]:
        article = await self.news_repository.get_article_by_id(article_id)
        if article is None:
            raise NewsNotFoundError()
        saved, already_saved = await self.saved_repository.save_article(session_id, article)
        return {
            "saved_id": saved["id"],
            "article_id": saved["article_id"],
            "already_saved": already_saved,
        }

    async def list_saved_articles(
        self,
        session_id: str,
        category: str | None,
        continent: str | None,
        sort: str,
    ) -> dict[str, Any]:
        if category is not None and category not in CATEGORIES:
            raise InvalidCategoryError()
        if continent is not None and continent not in CONTINENTS:
            raise InvalidContinentError()
        return await self.saved_repository.list_saved_articles(session_id, category, continent, sort)

    async def delete_saved_article(self, session_id: str, saved_id: str) -> dict[str, Any]:
        deleted = await self.saved_repository.delete_saved_article(session_id, saved_id)
        if not deleted:
            raise SavedArticleNotFoundError()
        return {"deleted_id": saved_id}
