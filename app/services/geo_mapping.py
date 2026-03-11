import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
COUNTRY_FILE = BASE_DIR / "data" / "country_centroids.json"
REGION_FILE = BASE_DIR / "data" / "region_centroids.json"


class GeoMapper:
    def __init__(self) -> None:
        self.country_data = _load_json(COUNTRY_FILE)
        self.region_data = _load_json(REGION_FILE)

    def infer_location(self, text: str) -> tuple[str | None, str | None, str | None]:
        lowered = text.lower()
        for country, data in self.country_data.items():
            aliases = [country.lower(), *[alias.lower() for alias in data.get("aliases", [])]]
            if any(alias in lowered for alias in aliases):
                return country, data.get("region"), data.get("continent")

        for region, data in self.region_data.items():
            aliases = [region.lower(), *[alias.lower() for alias in data.get("aliases", [])]]
            if any(alias in lowered for alias in aliases):
                return None, region, data.get("continent")

        return None, None, None

    def resolve_coordinates(self, country: str | None, region: str | None) -> tuple[float | None, float | None]:
        if country and country in self.country_data:
            data = self.country_data[country]
            return data.get("lat"), data.get("lng")
        if region and region in self.region_data:
            data = self.region_data[region]
            return data.get("lat"), data.get("lng")
        return None, None


@lru_cache(maxsize=1)
def get_geo_mapper() -> GeoMapper:
    return GeoMapper()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))
