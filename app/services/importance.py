from datetime import datetime, timezone

from app.core.constants import HIGH_INTENSITY_KEYWORDS, PIN_COLORS


def calculate_importance(category: str, title: str, summary: str, published_at: datetime | None) -> int:
    score = 2
    if published_at is not None:
        now = datetime.now(timezone.utc)
        age_hours = (now - published_at).total_seconds() / 3600
        if age_hours <= 12:
            score += 1
        if age_hours <= 72:
            score += 1

    text = f"{title} {summary}".lower()
    matches = sum(1 for keyword in HIGH_INTENSITY_KEYWORDS.get(category, []) if keyword in text)
    if matches >= 1:
        score += 1
    if matches >= 2:
        score += 1
    return max(1, min(score, 5))


def pin_size_for_importance(importance: int) -> str:
    if importance >= 5:
        return "large"
    if importance >= 3:
        return "medium"
    return "small"


def pin_color_for_category(category: str) -> str:
    return PIN_COLORS.get(category, "#64748B")
