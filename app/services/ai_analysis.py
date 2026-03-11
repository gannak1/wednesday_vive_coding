import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.repositories.news_repository import NewsRepository

IMPACT_LABELS = {
    "oil": "유가",
    "energy": "에너지",
    "gold": "금",
    "shipping": "해운",
    "supply_chain": "공급망",
    "supplychain": "공급망",
    "transport": "교통",
    "industry": "산업",
    "fx": "환율",
    "rates": "금리",
    "equities": "주식시장",
    "stocks": "주식시장",
    "policy": "정책",
    "trade": "무역",
    "sentiment": "시장 심리",
    "market": "시장",
    "inflation": "물가",
    "currency": "통화",
    "bonds": "채권",
    "logistics": "물류",
}

DEFAULT_IMPACTS = {
    "war": {
        "유가": "공급 불안 우려로 가격 변동성이 커질 수 있습니다.",
        "금": "위험 회피 심리로 수요가 늘 수 있습니다.",
        "해운": "운송 비용과 보험료 부담이 높아질 수 있습니다.",
    },
    "economy": {
        "환율": "통화 가치 변동성이 확대될 수 있습니다.",
        "금리": "시장 기대가 바뀌며 금리 전망이 흔들릴 수 있습니다.",
        "주식시장": "업종별로 차별화된 흐름이 나타날 수 있습니다.",
    },
    "disaster": {
        "공급망": "생산과 납기 일정에 차질이 생길 수 있습니다.",
        "교통": "항공, 항만, 도로 운영이 일시적으로 흔들릴 수 있습니다.",
        "산업": "피해 지역 중심으로 생산성이 낮아질 수 있습니다.",
    },
    "politics": {
        "정책": "정책 우선순위와 집행 속도가 바뀔 수 있습니다.",
        "무역": "대외 협상과 규제 기조에 변화가 생길 수 있습니다.",
        "시장 심리": "불확실성 확대로 투자 심리가 흔들릴 수 있습니다.",
    },
    "default": {
        "시장": "관련 시장과 정책 환경의 변동성이 커질 수 있습니다.",
    },
}


class AIAnalysisService:
    def __init__(self, database: Any) -> None:
        self.settings = get_settings()
        self.repository = NewsRepository(database)

    async def generate_pending_analyses(self, limit: int = 50) -> int:
        candidates = await self.repository.list_ai_candidates(limit=limit)
        if not candidates:
            return 0

        if not self.settings.openai_api_key:
            completed = 0
            for article in candidates:
                attempts = int(article.get("ai_attempts", 0)) + 1
                analysis = self._build_demo_analysis(article)
                await self.repository.mark_ai_completed(article["id"], analysis, attempts)
                completed += 1
            return completed

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        completed = 0

        for article in candidates:
            attempts = int(article.get("ai_attempts", 0)) + 1
            try:
                analysis = await self._analyze_article(client, article)
            except Exception:
                await self.repository.mark_ai_failed(article["id"], attempts)
                continue
            await self.repository.mark_ai_completed(article["id"], analysis, attempts)
            completed += 1

        return completed

    async def _analyze_article(self, client: AsyncOpenAI, article: dict[str, Any]) -> dict[str, Any]:
        prompt = {
            "title": article.get("title"),
            "summary": article.get("summary"),
            "category": article.get("category"),
            "country": article.get("country"),
            "continent": article.get("continent"),
            "region": article.get("region"),
            "source": article.get("source"),
            "published_at": str(article.get("published_at")),
        }

        completion = await client.chat.completions.create(
            model=self.settings.openai_model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize global news in Korean JSON. "
                        "Return only a JSON object with interpretation, prediction, and impact keys. "
                        "interpretation and prediction must be short Korean strings. "
                        "impact must be a flat JSON object with 1 to 3 user-facing labels as keys and short Korean explanations as values. "
                        "Do not return nested objects, arrays, numbers, or English-only labels."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False),
                },
            ],
        )
        raw_content = completion.choices[0].message.content or "{}"
        parsed = json.loads(raw_content)
        return self._normalize_analysis(parsed, article)

    def _build_demo_analysis(self, article: dict[str, Any]) -> dict[str, Any]:
        category = article.get("category")
        region = article.get("region") or article.get("country") or article.get("continent") or "해당 지역"
        title = article.get("title") or "이 기사"

        templates = {
            "war": {
                "interpretation": f"{title}는 {region}의 안보 불안과 물류 리스크 확대를 시사합니다.",
                "prediction": "단기적으로 에너지 가격과 안전자산 선호가 함께 커질 가능성이 있습니다.",
                "impact": DEFAULT_IMPACTS["war"],
            },
            "economy": {
                "interpretation": f"{title}는 정책 기대와 실물 경기 둔화가 동시에 반영된 경제 신호입니다.",
                "prediction": "환율과 금리 기대가 흔들리면서 시장 변동성이 커질 수 있습니다.",
                "impact": DEFAULT_IMPACTS["economy"],
            },
            "disaster": {
                "interpretation": f"{title}는 {region}의 공급망과 교통 인프라에 직접 부담을 줄 수 있는 재난 이슈입니다.",
                "prediction": "단기적으로 운송 지연과 생산 차질이 이어질 가능성이 있습니다.",
                "impact": DEFAULT_IMPACTS["disaster"],
            },
            "politics": {
                "interpretation": f"{title}는 정책 방향과 투자 심리를 바꿀 수 있는 정치 이벤트입니다.",
                "prediction": "예산, 외교, 규제 방향이 구체화되기 전까지 관망 심리가 이어질 수 있습니다.",
                "impact": DEFAULT_IMPACTS["politics"],
            },
        }
        return templates.get(
            category,
            {
                "interpretation": f"{title}는 주요 지역 이슈로 해석됩니다.",
                "prediction": "관련 시장과 정책 환경에 단기 변동성을 줄 수 있습니다.",
                "impact": DEFAULT_IMPACTS["default"],
            },
        )

    def _normalize_analysis(self, parsed: dict[str, Any], article: dict[str, Any]) -> dict[str, Any]:
        category = article.get("category")
        interpretation = self._normalize_text(parsed.get("interpretation"))
        prediction = self._normalize_text(parsed.get("prediction"))

        if not interpretation:
            interpretation = self._build_demo_analysis(article)["interpretation"]
        if not prediction:
            prediction = self._build_demo_analysis(article)["prediction"]

        return {
            "interpretation": interpretation,
            "prediction": prediction,
            "impact": self._normalize_impact(parsed.get("impact"), category),
        }

    def _normalize_text(self, value: Any) -> str | None:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned[:300] if cleaned else None
        return None

    def _normalize_impact(self, value: Any, category: str | None) -> dict[str, str]:
        normalized: dict[str, str] = {}

        if isinstance(value, dict):
            for raw_key, raw_value in value.items():
                label = self._label_for_key(raw_key)
                detail = self._impact_value_to_text(raw_value)
                if label and detail:
                    normalized[label] = detail
                if len(normalized) >= 3:
                    break
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                label = self._label_for_key(item.get("label") or item.get("name") or item.get("key"))
                detail = self._impact_value_to_text(item.get("effect") or item.get("value") or item.get("description"))
                if label and detail:
                    normalized[label] = detail
                if len(normalized) >= 3:
                    break
        else:
            detail = self._impact_value_to_text(value)
            if detail:
                normalized[self._default_label(category)] = detail

        if normalized:
            return normalized
        return dict(DEFAULT_IMPACTS.get(category or "", DEFAULT_IMPACTS["default"]))

    def _label_for_key(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        lowered = cleaned.lower().replace("-", "_").replace(" ", "_")
        return IMPACT_LABELS.get(lowered) or cleaned

    def _impact_value_to_text(self, value: Any) -> str | None:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned[:120] if cleaned else None
        if isinstance(value, dict):
            for key in ("effect", "summary", "description", "value", "impact"):
                nested = self._impact_value_to_text(value.get(key))
                if nested:
                    return nested
            return None
        if isinstance(value, (int, float)):
            return str(value)
        return None

    def _default_label(self, category: str | None) -> str:
        defaults = {
            "war": "안전자산",
            "economy": "시장",
            "disaster": "공급망",
            "politics": "정책",
        }
        return defaults.get(category or "", "시장")
