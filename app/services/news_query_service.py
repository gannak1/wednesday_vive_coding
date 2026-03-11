from typing import Any

from app.core.config import get_settings
from app.core.constants import CATEGORIES, CONTINENTS
from app.core.exceptions import InvalidCategoryError, InvalidContinentError, NewsNotFoundError, NewsSourceUnavailableError
from app.repositories.news_repository import NewsRepository
from app.services.news_ingestion import NewsIngestionService


class NewsQueryService:
    def __init__(self, database: Any) -> None:
        self.settings = get_settings()
        self.database = database
        self.repository = NewsRepository(database)

    async def get_home_data(self, continent: str | None, keyword: str | None, limit: int) -> dict[str, Any]:
        self._validate_continent(continent)
        await self._refresh_live_articles_if_needed()
        data = await self.repository.get_home_items(continent=continent, keyword=keyword, limit=limit)
        if not data["map_pins"] and not data["top_headlines"] and not await self.repository.has_articles():
            raise NewsSourceUnavailableError()
        return data

    async def get_category_data(
        self,
        category: str,
        continent: str | None,
        keyword: str | None,
        sort: str,
        limit: int,
    ) -> dict[str, Any]:
        self._validate_category(category)
        self._validate_continent(continent)
        await self._refresh_live_articles_if_needed()
        return await self.repository.get_category_articles(category, continent, keyword, sort, limit)

    async def get_continent_data(
        self,
        continent: str,
        category: str | None,
        keyword: str | None,
        limit: int,
    ) -> dict[str, Any]:
        self._validate_continent(continent)
        if category is not None:
            self._validate_category(category)
        await self._refresh_live_articles_if_needed()
        return await self.repository.get_continent_articles(continent, category, keyword, limit)

    async def search_news(
        self,
        query: str,
        continent: str | None,
        category: str | None,
        limit: int,
        page: int,
    ) -> dict[str, Any]:
        self._validate_continent(continent)
        if category is not None:
            self._validate_category(category)
        await self._refresh_live_articles_if_needed()
        return await self.repository.search_articles(query, continent, category, limit, page)

    async def get_article_detail(self, article_id: str) -> dict[str, Any]:
        article = await self.repository.get_article_by_id(article_id)
        if article is None:
            raise NewsNotFoundError()
        return article

    async def get_article_analysis(self, article_id: str) -> dict[str, Any]:
        analysis = await self.repository.get_article_analysis(article_id)
        if analysis is None:
            raise NewsNotFoundError()
        return analysis

    async def _refresh_live_articles_if_needed(self) -> None:
        if not self.settings.newsapi_api_key:
            return
        if await self.repository.count_live_articles() > 0:
            return
        await NewsIngestionService(self.database).collect_latest_news()

    def _validate_category(self, category: str | None) -> None:
        if category is not None and category not in CATEGORIES:
            raise InvalidCategoryError()

    def _validate_continent(self, continent: str | None) -> None:
        if continent is not None and continent not in CONTINENTS:
            raise InvalidContinentError()
