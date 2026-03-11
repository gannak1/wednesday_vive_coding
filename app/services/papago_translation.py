import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.constants import CATEGORY_LABELS
from app.repositories.news_repository import NewsRepository


class PapagoTranslationService:
    def __init__(self, database: Any) -> None:
        self.settings = get_settings()
        self.repository = NewsRepository(database)
        self.category_cache: dict[str, str] = {}

    async def translate_pending_articles(self, limit: int = 50) -> int:
        if not self.settings.papago_configured:
            return 0

        candidates = await self.repository.list_translation_candidates(limit=limit)
        if not candidates:
            return 0

        headers = {
            "x-ncp-apigw-api-key-id": self.settings.papago_header_key_id or "",
            "x-ncp-apigw-api-key": self.settings.papago_header_key or "",
        }
        completed = 0

        async with httpx.AsyncClient(base_url=self.settings.papago_base_url, headers=headers, timeout=30.0) as client:
            for article in candidates:
                attempts = int(article.get("translation_attempts", 0)) + 1
                try:
                    translated = await self._translate_article(client, article)
                except Exception:
                    await self.repository.mark_translation_failed(article["id"], attempts)
                    continue
                await self.repository.mark_translation_completed(article["id"], translated, attempts)
                completed += 1

        return completed

    async def _translate_article(self, client: httpx.AsyncClient, article: dict[str, Any]) -> dict[str, Any]:
        category = article.get("category") or ""
        category_label = self.category_cache.get(category)
        if category_label is None:
            category_label = await self._translate_text(client, category)
            if not category_label:
                category_label = CATEGORY_LABELS.get(category, category)
            self.category_cache[category] = category_label

        return {
            "title_ko": await self._translate_text(client, article.get("title")),
            "summary_ko": await self._translate_text(client, article.get("summary")),
            "content_ko": await self._translate_text(client, article.get("content")),
            "category_label_ko": category_label,
        }

    async def _translate_text(self, client: httpx.AsyncClient, text: str | None) -> str | None:
        if not text:
            return None

        chunks = self._chunk_text(text)
        if not chunks:
            return None

        translated_chunks: list[str] = []
        for chunk in chunks:
            response = await client.post(
                "/nmt/v1/translation",
                data={
                    "source": self.settings.papago_source_language,
                    "target": self.settings.papago_target_language,
                    "text": chunk,
                },
            )
            response.raise_for_status()
            translated_chunks.append(self._extract_translated_text(response.json()))

        translated = "\n\n".join(part.strip() for part in translated_chunks if part and part.strip()).strip()
        return translated or None

    def _extract_translated_text(self, payload: dict[str, Any]) -> str:
        translated_text = (
            payload.get("message", {})
            .get("result", {})
            .get("translatedText")
        )
        if translated_text:
            return str(translated_text)

        translated_text = payload.get("translatedText")
        if translated_text:
            return str(translated_text)

        error_message = payload.get("errorMessage") or payload.get("message") or "Papago 번역 응답을 해석하지 못했습니다."
        raise ValueError(str(error_message))

    def _chunk_text(self, text: str, max_chars: int = 4500) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", normalized) if paragraph.strip()]
        if not paragraphs:
            paragraphs = [normalized]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_text(paragraph, max_chars))
                continue

            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)
        return chunks

    def _split_long_text(self, text: str, max_chars: int) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._hard_split(sentence, max_chars))
                continue

            candidate = f"{current} {sentence}" if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)
        return chunks

    def _hard_split(self, text: str, max_chars: int) -> list[str]:
        return [text[index:index + max_chars].strip() for index in range(0, len(text), max_chars) if text[index:index + max_chars].strip()]
