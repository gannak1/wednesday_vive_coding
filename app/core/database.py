import inspect
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo import AsyncMongoClient

from app.core.config import get_settings

_client: AsyncMongoClient[Any] | None = None


async def connect_database() -> Any:
    global _client
    settings = get_settings()
    _client = AsyncMongoClient(settings.mongodb_uri)
    return _client[settings.mongodb_db_name]


async def close_database() -> None:
    global _client
    if _client is not None:
        result = _client.close()
        if inspect.isawaitable(result):
            await result
        _client = None


async def ensure_indexes(database: Any) -> None:
    settings = get_settings()
    news = database[settings.news_collection_name]
    saved = database[settings.saved_collection_name]

    news_indexes = [
        IndexModel([("id", ASCENDING)], unique=True, name="news_id_unique"),
        IndexModel(
            [("original_url", ASCENDING)],
            unique=True,
            name="news_original_url_unique",
            partialFilterExpression={"original_url": {"$type": "string"}},
        ),
        IndexModel([("category", ASCENDING)], name="news_category_idx"),
        IndexModel([("continent", ASCENDING)], name="news_continent_idx"),
        IndexModel([("published_at", DESCENDING)], name="news_published_desc_idx"),
        IndexModel([("importance", DESCENDING)], name="news_importance_desc_idx"),
        IndexModel([("ai_status", ASCENDING)], name="news_ai_status_idx"),
        IndexModel([("translation_status", ASCENDING)], name="news_translation_status_idx"),
        IndexModel([("updated_at", DESCENDING)], name="news_updated_desc_idx"),
        IndexModel([("translated_at", DESCENDING)], name="news_translated_desc_idx"),
        IndexModel([("keywords", ASCENDING)], name="news_keywords_idx"),
        IndexModel([("title", "text"), ("summary", "text")], name="news_text_idx"),
    ]

    saved_indexes = [
        IndexModel([("id", ASCENDING)], unique=True, name="saved_id_unique"),
        IndexModel(
            [("session_id", ASCENDING), ("article_id", ASCENDING)],
            unique=True,
            name="saved_session_article_unique",
        ),
        IndexModel(
            [("session_id", ASCENDING), ("saved_at", DESCENDING)],
            name="saved_session_saved_at_idx",
        ),
        IndexModel(
            [("session_id", ASCENDING), ("category", ASCENDING)],
            name="saved_session_category_idx",
        ),
    ]

    await news.create_indexes(news_indexes)
    await saved.create_indexes(saved_indexes)
