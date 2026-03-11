import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING

from app.core.config import get_settings
from app.core.constants import CATEGORY_LABELS


class SavedRepository:
    def __init__(self, database: Any) -> None:
        settings = get_settings()
        self.collection = database[settings.saved_collection_name]

    async def save_article(self, session_id: str, article: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = await self.collection.find_one({"session_id": session_id, "article_id": article["id"]})
        if existing is not None:
            return self._serialize_saved(existing), True

        document = {
            "id": f"saved_{uuid.uuid4().hex}",
            "session_id": session_id,
            "article_id": article["id"],
            "title": article.get("title"),
            "category": article.get("category"),
            "category_label": article.get("category_label") or CATEGORY_LABELS.get(article.get("category"), article.get("category")),
            "continent": article.get("continent"),
            "region": article.get("region"),
            "source": article.get("source"),
            "summary": article.get("summary"),
            "saved_at": datetime.now(timezone.utc),
        }
        await self.collection.insert_one(document)
        return self._serialize_saved(document), False

    async def list_saved_articles(
        self,
        session_id: str,
        category: str | None,
        continent: str | None,
        sort: str,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {"session_id": session_id}
        if category:
            filters["category"] = category
        if continent:
            filters["continent"] = continent

        sort_fields = [("saved_at", DESCENDING)]
        if sort == "category":
            sort_fields = [("category", ASCENDING), ("saved_at", DESCENDING)]

        cursor = self.collection.find(filters).sort(sort_fields)
        articles = [self._serialize_saved(doc) async for doc in cursor]
        return {"articles": articles}

    async def delete_saved_article(self, session_id: str, saved_id: str) -> bool:
        result = await self.collection.delete_one({"session_id": session_id, "id": saved_id})
        return result.deleted_count > 0

    def _serialize_saved(self, document: dict[str, Any]) -> dict[str, Any]:
        saved_at = document.get("saved_at")
        if isinstance(saved_at, datetime):
            saved_at = saved_at.astimezone(timezone.utc).isoformat()
        category = document.get("category")
        return {
            "id": document.get("id"),
            "article_id": document.get("article_id"),
            "title": document.get("title"),
            "category": category,
            "category_label": document.get("category_label") or CATEGORY_LABELS.get(category, category),
            "continent": document.get("continent"),
            "region": document.get("region"),
            "source": document.get("source"),
            "summary": document.get("summary"),
            "saved_at": saved_at,
        }
