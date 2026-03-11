import re
from datetime import datetime, timezone
from typing import Any

from app.core.constants import CATEGORY_PRIORITY, CATEGORY_QUERIES
from app.services.geo_mapping import get_geo_mapper
from app.services.importance import calculate_importance, pin_color_for_category, pin_size_for_importance


class NewsNormalizer:
    def __init__(self) -> None:
        self.geo_mapper = get_geo_mapper()

    def normalize(self, raw_article: dict[str, Any], seed_category: str) -> dict[str, Any] | None:
        title = (raw_article.get("title") or "").strip()
        if not title or title == "[Removed]":
            return None

        summary = (raw_article.get("description") or raw_article.get("content") or title).strip()
        content = raw_article.get("content")
        published_at = _parse_datetime(raw_article.get("publishedAt"))

        category = self._classify(seed_category, title, summary)
        if category is None:
            return None

        country, region, continent = self.geo_mapper.infer_location(f"{title} {summary}")
        lat, lng = self.geo_mapper.resolve_coordinates(country, region)
        importance = calculate_importance(category, title, summary, published_at)

        return {
            "external_id": raw_article.get("url"),
            "original_url": raw_article.get("url"),
            "title": title,
            "source": (raw_article.get("source") or {}).get("name") or "Unknown",
            "published_at": published_at or datetime.now(timezone.utc),
            "summary": summary,
            "content": content,
            "country": country,
            "continent": continent,
            "region": region,
            "category": category,
            "keywords": self._extract_keywords(title, summary, category),
            "lat": lat,
            "lng": lng,
            "importance": importance,
            "pin_size": pin_size_for_importance(importance),
            "pin_color": pin_color_for_category(category),
        }

    def _classify(self, seed_category: str, title: str, summary: str) -> str | None:
        text = f"{title} {summary}".lower()
        scores = {category: 0 for category in CATEGORY_QUERIES}
        keyword_sets = {
            "war": ["war", "military", "missile", "conflict", "invasion", "ceasefire"],
            "economy": ["economy", "inflation", "interest rate", "trade", "market", "tariff"],
            "disaster": ["earthquake", "flood", "wildfire", "hurricane", "typhoon", "drought"],
            "politics": ["election", "government", "parliament", "diplomacy", "summit", "sanctions"],
        }

        for category, keywords in keyword_sets.items():
            scores[category] = sum(1 for keyword in keywords if keyword in text)

        if max(scores.values(), default=0) == 0:
            return None

        highest = max(scores.values())
        candidates = [category for category, score in scores.items() if score == highest]
        if seed_category in candidates:
            return seed_category
        for category in CATEGORY_PRIORITY:
            if category in candidates:
                return category
        return candidates[0]

    def _extract_keywords(self, title: str, summary: str, category: str) -> list[str]:
        text = f"{title} {summary}".lower()
        matches = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text)
        keywords: list[str] = []
        for keyword in [category, *matches]:
            if keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 10:
                break
        return keywords


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)
