import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.constants import CATEGORY_QUERIES
from app.repositories.news_repository import NewsRepository
from app.services.news_normalizer import NewsNormalizer


class NewsIngestionService:
    def __init__(self, database: Any) -> None:
        self.settings = get_settings()
        self.repository = NewsRepository(database)
        self.normalizer = NewsNormalizer()
        self.demo_articles_path = Path(__file__).resolve().parents[1] / "data" / "demo_articles.json"

    async def collect_latest_news(self) -> int:
        if not self.settings.newsapi_api_key:
            return await self.seed_demo_articles_if_empty()

        since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        deduped: dict[str, dict[str, Any]] = {}

        async with httpx.AsyncClient(base_url="https://newsapi.org", timeout=30.0) as client:
            for category, query in CATEGORY_QUERIES.items():
                try:
                    response = await client.get(
                        "/v2/everything",
                        params={
                            "q": query,
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": 25,
                            "from": since,
                            "apiKey": self.settings.newsapi_api_key,
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue

                for raw_article in response.json().get("articles", []):
                    normalized = self.normalizer.normalize(raw_article, category)
                    if normalized is None:
                        continue
                    normalized["data_source"] = "live"
                    key = normalized.get("original_url") or (
                        f"{normalized.get('source')}::{normalized.get('title')}::{normalized.get('published_at')}"
                    )
                    deduped[key] = normalized

        upserted = 0
        for article in deduped.values():
            await self.repository.upsert_article(article)
            upserted += 1

        if upserted > 0:
            await self.repository.delete_demo_articles()
        return upserted

    async def seed_demo_articles_if_empty(self) -> int:
        if await self.repository.has_articles():
            return 0

        if not self.demo_articles_path.exists():
            return 0

        raw_articles = json.loads(self.demo_articles_path.read_text(encoding="utf-8-sig"))
        seeded = 0
        for article in raw_articles:
            demo_article = {
                **article,
                "data_source": "demo",
                "original_url": article.get("original_url") or f"demo://{article['category']}/{seeded + 1}",
                "external_id": article.get("external_id") or f"demo_{seeded + 1}",
                "published_at": self._parse_datetime(article.get("published_at")),
            }
            await self.repository.upsert_article(demo_article)
            seeded += 1
        return seeded

    async def cleanup_old_news(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return await self.repository.delete_older_than(cutoff)

    def _parse_datetime(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
