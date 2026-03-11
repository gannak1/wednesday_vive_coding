import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import DESCENDING

from app.core.config import get_settings
from app.core.constants import CATEGORY_LABELS


class NewsRepository:
    def __init__(self, database: Any) -> None:
        settings = get_settings()
        self.collection = database[settings.news_collection_name]

    async def has_articles(self) -> bool:
        return await self.collection.count_documents({}, limit=1) > 0

    async def get_home_items(self, continent: str | None, keyword: str | None, limit: int) -> dict[str, Any]:
        filters = self._build_filters(continent=continent, keyword=keyword)
        map_filters = {**filters, "lat": {"$ne": None}, "lng": {"$ne": None}}

        map_cursor = self.collection.find(map_filters).sort(
            [("importance", DESCENDING), ("published_at", DESCENDING)]
        )
        headline_cursor = self.collection.find(filters).sort(
            [("importance", DESCENDING), ("published_at", DESCENDING)]
        ).limit(limit)

        map_pins = [self._serialize_pin(doc) async for doc in map_cursor]
        top_headlines = [self._serialize_article_card(doc) async for doc in headline_cursor]
        return {"map_pins": map_pins, "top_headlines": top_headlines}

    async def get_category_articles(
        self,
        category: str,
        continent: str | None,
        keyword: str | None,
        sort: str,
        limit: int,
    ) -> dict[str, Any]:
        filters = self._build_filters(category=category, continent=continent, keyword=keyword)
        sort_fields = self._resolve_sort(sort)
        cursor = self.collection.find(filters).sort(sort_fields).limit(limit)
        articles = [self._serialize_article_summary(doc) async for doc in cursor]
        return {"category": category, "articles": articles}

    async def get_continent_articles(
        self,
        continent: str,
        category: str | None,
        keyword: str | None,
        limit: int,
    ) -> dict[str, Any]:
        filters = self._build_filters(category=category, continent=continent, keyword=keyword)
        cursor = self.collection.find(filters).sort(
            [("importance", DESCENDING), ("published_at", DESCENDING)]
        ).limit(limit)
        articles = [self._serialize_article_summary(doc) async for doc in cursor]
        return {"continent": continent, "articles": articles}

    async def search_articles(
        self,
        query: str,
        continent: str | None,
        category: str | None,
        limit: int,
        page: int,
    ) -> dict[str, Any]:
        filters = self._build_filters(category=category, continent=continent, keyword=query)
        total = await self.collection.count_documents(filters)
        skip = max(page - 1, 0) * limit
        cursor = self.collection.find(filters).sort(
            [("importance", DESCENDING), ("published_at", DESCENDING)]
        ).skip(skip).limit(limit)
        articles = [self._serialize_article_summary(doc) async for doc in cursor]
        return {
            "query": query,
            "total": total,
            "page": page,
            "page_size": limit,
            "articles": articles,
        }

    async def get_article_by_id(self, article_id: str) -> dict[str, Any] | None:
        document = await self.collection.find_one({"id": article_id})
        if document is None:
            return None
        return self._serialize_article_detail(document)

    async def get_article_analysis(self, article_id: str) -> dict[str, Any] | None:
        document = await self.collection.find_one({"id": article_id})
        if document is None:
            return None
        return {
            "article_id": article_id,
            "ai_status": document.get("ai_status", "pending"),
            "interpretation": document.get("ai_interpretation"),
            "prediction": document.get("ai_prediction"),
            "impact": document.get("ai_impact"),
        }

    async def upsert_article(self, article: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        existing = await self._find_existing(article)

        if existing is not None:
            update_doc = {**article}
            update_doc["id"] = existing["id"]
            update_doc["created_at"] = existing.get("created_at", now)
            update_doc["updated_at"] = now
            if self._content_changed(existing, article):
                update_doc["ai_status"] = "pending"
                update_doc["ai_interpretation"] = None
                update_doc["ai_prediction"] = None
                update_doc["ai_impact"] = None
                update_doc["ai_generated_at"] = None
                update_doc["ai_attempts"] = 0
                update_doc["translation_status"] = "pending"
                update_doc["title_ko"] = None
                update_doc["summary_ko"] = None
                update_doc["content_ko"] = None
                update_doc["category_label_ko"] = None
                update_doc["translated_at"] = None
                update_doc["translation_attempts"] = 0
                update_doc["translation_provider"] = None
            else:
                update_doc["ai_status"] = existing.get("ai_status", "pending")
                update_doc["ai_interpretation"] = existing.get("ai_interpretation")
                update_doc["ai_prediction"] = existing.get("ai_prediction")
                update_doc["ai_impact"] = existing.get("ai_impact")
                update_doc["ai_generated_at"] = existing.get("ai_generated_at")
                update_doc["ai_attempts"] = existing.get("ai_attempts", 0)
                update_doc["translation_status"] = existing.get("translation_status", "pending")
                update_doc["title_ko"] = existing.get("title_ko")
                update_doc["summary_ko"] = existing.get("summary_ko")
                update_doc["content_ko"] = existing.get("content_ko")
                update_doc["category_label_ko"] = existing.get("category_label_ko")
                update_doc["translated_at"] = existing.get("translated_at")
                update_doc["translation_attempts"] = existing.get("translation_attempts", 0)
                update_doc["translation_provider"] = existing.get("translation_provider")
            await self.collection.update_one({"_id": existing["_id"]}, {"$set": update_doc})
            return update_doc

        document = {
            **article,
            "id": article.get("id") or f"news_{uuid.uuid4().hex}",
            "ai_status": "pending",
            "ai_interpretation": None,
            "ai_prediction": None,
            "ai_impact": None,
            "ai_generated_at": None,
            "ai_attempts": 0,
            "translation_status": article.get("translation_status") or "pending",
            "title_ko": article.get("title_ko"),
            "summary_ko": article.get("summary_ko"),
            "content_ko": article.get("content_ko"),
            "category_label_ko": article.get("category_label_ko"),
            "translated_at": article.get("translated_at"),
            "translation_attempts": article.get("translation_attempts", 0),
            "translation_provider": article.get("translation_provider"),
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(document)
        return document

    async def list_ai_candidates(self, limit: int = 50) -> list[dict[str, Any]]:
        retry_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        cursor = self.collection.find(
            {
                "ai_attempts": {"$lt": 3},
                "$or": [
                    {"ai_status": "pending"},
                    {"ai_status": "failed", "updated_at": {"$lte": retry_cutoff}},
                ],
            }
        ).sort([("published_at", DESCENDING)]).limit(limit)
        return [doc async for doc in cursor]

    async def list_translation_candidates(self, limit: int = 50) -> list[dict[str, Any]]:
        retry_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        cursor = self.collection.find(
            {
                "translation_attempts": {"$lt": 3},
                "$or": [
                    {"translation_status": {"$exists": False}},
                    {"translation_status": "pending"},
                    {"translation_status": "failed", "updated_at": {"$lte": retry_cutoff}},
                ],
            }
        ).sort([("published_at", DESCENDING)]).limit(limit)
        return [doc async for doc in cursor]

    async def mark_ai_completed(self, article_id: str, analysis: dict[str, Any], attempts: int) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"id": article_id},
            {
                "$set": {
                    "ai_status": "completed",
                    "ai_interpretation": analysis.get("interpretation"),
                    "ai_prediction": analysis.get("prediction"),
                    "ai_impact": analysis.get("impact"),
                    "ai_generated_at": now,
                    "ai_attempts": attempts,
                    "updated_at": now,
                }
            },
        )

    async def mark_ai_failed(self, article_id: str, attempts: int) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"id": article_id},
            {
                "$set": {
                    "ai_status": "failed",
                    "ai_attempts": attempts,
                    "updated_at": now,
                }
            },
        )

    async def mark_translation_completed(self, article_id: str, translation: dict[str, Any], attempts: int) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"id": article_id},
            {
                "$set": {
                    "translation_status": "completed",
                    "title_ko": translation.get("title_ko"),
                    "summary_ko": translation.get("summary_ko"),
                    "content_ko": translation.get("content_ko"),
                    "category_label_ko": translation.get("category_label_ko"),
                    "translated_at": now,
                    "translation_provider": "papago",
                    "translation_attempts": attempts,
                    "updated_at": now,
                }
            },
        )

    async def mark_translation_failed(self, article_id: str, attempts: int) -> None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"id": article_id},
            {
                "$set": {
                    "translation_status": "failed",
                    "translation_attempts": attempts,
                    "updated_at": now,
                }
            },
        )

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self.collection.delete_many({"published_at": {"$lt": cutoff}})
        return int(result.deleted_count)

    async def delete_demo_articles(self) -> int:
        result = await self.collection.delete_many(
            {
                "$or": [
                    {"data_source": "demo"},
                    {"original_url": {"$regex": r"^demo://", "$options": "i"}},
                    {"external_id": {"$regex": r"^demo_", "$options": "i"}},
                    {"source": {"$regex": r"^Demo", "$options": "i"}},
                ]
            }
        )
        return int(result.deleted_count)

    async def count_live_articles(self) -> int:
        live_count = await self.collection.count_documents({"data_source": "live"})
        if live_count > 0:
            return live_count
        return await self.collection.count_documents(
            {
                "$nor": [
                    {"data_source": "demo"},
                    {"original_url": {"$regex": r"^demo://", "$options": "i"}},
                    {"external_id": {"$regex": r"^demo_", "$options": "i"}},
                    {"source": {"$regex": r"^Demo", "$options": "i"}},
                ]
            }
        )

    async def _find_existing(self, article: dict[str, Any]) -> dict[str, Any] | None:
        original_url = article.get("original_url")
        if original_url:
            existing = await self.collection.find_one({"original_url": original_url})
            if existing is not None:
                return existing
        return await self.collection.find_one(
            {
                "source": article.get("source"),
                "title": article.get("title"),
                "published_at": article.get("published_at"),
            }
        )

    def _content_changed(self, existing: dict[str, Any], new_article: dict[str, Any]) -> bool:
        return (
            existing.get("title") != new_article.get("title")
            or existing.get("summary") != new_article.get("summary")
            or existing.get("content") != new_article.get("content")
            or existing.get("category") != new_article.get("category")
            or existing.get("data_source") != new_article.get("data_source")
        )

    def _build_filters(
        self,
        category: str | None = None,
        continent: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if category:
            filters["category"] = category
        if continent:
            filters["continent"] = continent
        if keyword:
            regex = {"$regex": keyword, "$options": "i"}
            filters["$or"] = [
                {"title": regex},
                {"title_ko": regex},
                {"summary": regex},
                {"summary_ko": regex},
                {"content": regex},
                {"content_ko": regex},
                {"keywords": regex},
                {"country": regex},
                {"region": regex},
                {"category_label_ko": regex},
            ]
        return filters

    def _resolve_sort(self, sort: str) -> list[tuple[str, int]]:
        if sort == "latest":
            return [("published_at", DESCENDING), ("importance", DESCENDING)]
        return [("importance", DESCENDING), ("published_at", DESCENDING)]

    def _serialize_pin(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": document.get("id"),
            "title": self._localized_text(document, "title"),
            "continent": document.get("continent"),
            "category": document.get("category"),
            "category_label": self._category_label(document),
            "lat": document.get("lat"),
            "lng": document.get("lng"),
            "importance": document.get("importance"),
            "pin_size": document.get("pin_size"),
            "pin_color": document.get("pin_color"),
        }

    def _serialize_article_card(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": document.get("id"),
            "title": self._localized_text(document, "title"),
            "category": document.get("category"),
            "category_label": self._category_label(document),
            "continent": document.get("continent"),
            "region": document.get("region"),
            "source": document.get("source"),
            "summary": self._localized_text(document, "summary"),
            "translation_status": document.get("translation_status", "pending"),
        }

    def _serialize_article_summary(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": document.get("id"),
            "title": self._localized_text(document, "title"),
            "title_original": document.get("title"),
            "source": document.get("source"),
            "published_at": self._serialize_datetime(document.get("published_at")),
            "summary": self._localized_text(document, "summary"),
            "summary_original": document.get("summary"),
            "country": document.get("country"),
            "continent": document.get("continent"),
            "region": document.get("region"),
            "category": document.get("category"),
            "category_label": self._category_label(document),
            "lat": document.get("lat"),
            "lng": document.get("lng"),
            "importance": document.get("importance"),
            "pin_size": document.get("pin_size"),
            "pin_color": document.get("pin_color"),
            "translation_status": document.get("translation_status", "pending"),
        }

    def _serialize_article_detail(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": document.get("id"),
            "title": self._localized_text(document, "title"),
            "title_original": document.get("title"),
            "source": document.get("source"),
            "published_at": self._serialize_datetime(document.get("published_at")),
            "summary": self._localized_text(document, "summary"),
            "summary_original": document.get("summary"),
            "content": self._localized_text(document, "content"),
            "content_original": document.get("content"),
            "country": document.get("country"),
            "continent": document.get("continent"),
            "region": document.get("region"),
            "category": document.get("category"),
            "category_label": self._category_label(document),
            "keywords": document.get("keywords", []),
            "lat": document.get("lat"),
            "lng": document.get("lng"),
            "importance": document.get("importance"),
            "pin_size": document.get("pin_size"),
            "pin_color": document.get("pin_color"),
            "translation_status": document.get("translation_status", "pending"),
        }

    def _localized_text(self, document: dict[str, Any], field_name: str) -> Any:
        return document.get(f"{field_name}_ko") or document.get(field_name)

    def _category_label(self, document: dict[str, Any]) -> str:
        category = document.get("category")
        return document.get("category_label_ko") or CATEGORY_LABELS.get(category, category)

    def _serialize_datetime(self, value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return value
